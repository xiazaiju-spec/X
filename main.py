from __future__ import annotations

import argparse
import os
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

from ai.llm_client import LLMClient
from data_provider.akshare_provider import AKShareProvider
from data_provider.base import MarketDataProvider
from data_provider.longbridge_provider import LongbridgeProvider
from data_provider.stooq_provider import StooqProvider
from data_provider.yfinance_provider import YFinanceProvider
from database.storage import SQLiteStorage
from indicators.technical import add_technical_indicators
from notify.email_sender import send_email_report
from notify.telegram import send_telegram_message
from report.dashboard import print_console_summary
from report.markdown_report import save_markdown_report
from scheduler.jobs import start_scheduler
from strategy.index_score import score_index
from strategy.stock_score import score_stock


def main() -> None:
    parser = argparse.ArgumentParser(description="AI stock decision dashboard")
    parser.add_argument("--once", action="store_true", help="Run one complete analysis")
    parser.add_argument("--schedule", action="store_true", help="Run APScheduler")
    parser.add_argument("--config", default="config.yaml", help="Path to config.yaml")
    args = parser.parse_args()

    load_dotenv()
    config = load_config(args.config)

    if args.schedule:
        cron = config.get("scheduler", {}).get("cron", "0 18 * * 1-5")
        timezone = config.get("app", {}).get("timezone", "Asia/Shanghai")
        start_scheduler(lambda: run_analysis(config), cron=cron, timezone=timezone)
        return

    run_analysis(config)


def run_analysis(config: dict[str, Any]) -> dict[str, Any]:
    run_date = date.today().isoformat()
    lookback_days = int(config.get("analysis", {}).get("lookback_days", 180))
    start = date.today() - timedelta(days=lookback_days)
    end = date.today()

    providers = build_providers()
    indices = analyze_indices(config.get("indices", []), providers, start, end)
    market_score_by_market = average_market_scores(config.get("indices", []), indices)
    stocks = analyze_stocks(config.get("watchlist", []), providers, start, end, market_score_by_market)

    payload = {
        "run_date": run_date,
        "indices": indices,
        "stocks": stocks,
        "market_score_by_market": market_score_by_market,
    }

    markdown = LLMClient().generate_report(payload)

    report_dir = config.get("app", {}).get("report_dir", "reports")
    report_path = save_markdown_report(report_dir, run_date, markdown)

    db_path = resolve_env_value(config.get("database", {}).get("path", "data/stock_dashboard.db"))
    SQLiteStorage(db_path).save_run(run_date, payload, markdown)

    send_notifications(run_date, markdown)
    print_console_summary(payload)
    print(f"\nReport saved: {report_path}")
    print(f"Database saved: {db_path}")
    return payload


def analyze_indices(
    items: list[dict[str, Any]],
    providers: dict[str, MarketDataProvider],
    start: date,
    end: date,
) -> list[dict[str, Any]]:
    results = []
    for item in items:
        try:
            df, source = fetch_with_fallback(item, providers, start, end)
            df = add_technical_indicators(df)
            result = score_index(item["name"], item["symbol"], df)
            result["source_provider"] = source["provider"]
            result["source_symbol"] = source["symbol"]
            results.append(result)
        except Exception as exc:
            results.append(error_score(item, "index", exc))
    return results


def analyze_stocks(
    items: list[dict[str, Any]],
    providers: dict[str, MarketDataProvider],
    start: date,
    end: date,
    market_score_by_market: dict[str, int],
) -> list[dict[str, Any]]:
    results = []
    for item in items:
        try:
            df, source = fetch_with_fallback(item, providers, start, end)
            df = add_technical_indicators(df)
            market_score = market_score_by_market.get(item.get("market"))
            result = score_stock(item["name"], item["symbol"], df, market_score=market_score)
            result["source_provider"] = source["provider"]
            result["source_symbol"] = source["symbol"]
            results.append(result)
        except Exception as exc:
            results.append(error_score(item, "stock", exc))
    return results


def build_providers() -> dict[str, MarketDataProvider]:
    return {
        "akshare": AKShareProvider(),
        "longbridge": LongbridgeProvider(),
        "stooq": StooqProvider(),
        "yfinance": YFinanceProvider(),
    }


def fetch_with_fallback(
    item: dict[str, Any],
    providers: dict[str, MarketDataProvider],
    start: date,
    end: date,
) -> tuple[Any, dict[str, str]]:
    errors = []
    for source in provider_candidates(item):
        provider_name = source["provider"]
        symbol = source["symbol"]
        provider = providers.get(provider_name)
        if provider is None:
            errors.append(f"{provider_name}:{symbol}: provider not configured")
            continue

        try:
            df = provider.fetch_daily(symbol, start, end)
            if df.empty:
                raise ValueError("empty data")
            return df, source
        except Exception as exc:
            errors.append(f"{provider_name}:{symbol}: {exc}")

    raise RuntimeError("All providers failed: " + " | ".join(errors))


def provider_candidates(item: dict[str, Any]) -> list[dict[str, str]]:
    candidates = [{"provider": item["provider"], "symbol": item["symbol"]}]
    fallbacks = item.get("fallback_providers")
    if fallbacks is None:
        fallbacks = default_fallbacks(item)

    for fallback in fallbacks:
        if isinstance(fallback, str):
            candidates.append({"provider": fallback, "symbol": item["symbol"]})
        else:
            candidates.append(
                {
                    "provider": fallback.get("provider", item["provider"]),
                    "symbol": fallback.get("symbol", item["symbol"]),
                }
            )

    deduped = []
    seen = set()
    for candidate in candidates:
        key = (candidate["provider"], candidate["symbol"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(candidate)
    return deduped


def default_fallbacks(item: dict[str, Any]) -> list[dict[str, str]]:
    market = item.get("market")
    symbol = item.get("symbol", "")
    if market == "HK":
        akshare_symbol = symbol.replace(".HK", "").zfill(5) if symbol.endswith(".HK") else symbol
        if item.get("provider") == "longbridge":
            return [
                {"provider": "yfinance", "symbol": symbol},
                {"provider": "akshare", "symbol": akshare_symbol},
                {"provider": "stooq", "symbol": symbol},
            ]
        return [
            {"provider": "longbridge", "symbol": symbol},
            {"provider": "akshare", "symbol": akshare_symbol},
            {"provider": "stooq", "symbol": symbol},
        ]
    if market == "US":
        if item.get("provider") == "longbridge":
            return [
                {"provider": "yfinance", "symbol": symbol},
                {"provider": "akshare", "symbol": symbol},
                {"provider": "stooq", "symbol": symbol},
            ]
        if symbol.startswith("^"):
            return [
                {"provider": "longbridge", "symbol": symbol},
                {"provider": "stooq", "symbol": symbol},
            ]
        return [
            {"provider": "longbridge", "symbol": symbol},
            {"provider": "akshare", "symbol": symbol},
            {"provider": "stooq", "symbol": symbol},
        ]
    return []


def average_market_scores(index_config: list[dict[str, Any]], index_scores: list[dict[str, Any]]) -> dict[str, int]:
    grouped: dict[str, list[int]] = {}
    config_by_symbol = {item["symbol"]: item for item in index_config}
    for score in index_scores:
        market = config_by_symbol.get(score["symbol"], {}).get("market")
        if market and score.get("score", 0) > 0:
            grouped.setdefault(market, []).append(int(score["score"]))
    return {market: round(sum(scores) / len(scores)) for market, scores in grouped.items() if scores}


def error_score(item: dict[str, Any], asset_type: str, exc: Exception) -> dict[str, Any]:
    return {
        "name": item.get("name", item.get("symbol", "")),
        "symbol": item.get("symbol", ""),
        "type": asset_type,
        "score": 0,
        "recommendation": "数据获取失败",
        "risk_level": "unknown",
        "risk_flags": [str(exc)],
        "reasons": [],
        "latest": {},
    }


def send_notifications(run_date: str, markdown: str) -> None:
    errors = []
    for sender in [send_telegram_message, lambda content: send_email_report(f"AI 股票决策日报 {run_date}", content)]:
        try:
            sender(markdown)
        except Exception as exc:
            errors.append(str(exc))
    if errors:
        print("Notification warnings:")
        for error in errors:
            print(f"- {error}")


def load_config(path: str) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def resolve_env_value(value: str) -> str:
    if not isinstance(value, str):
        return str(value)
    if value.startswith("${") and value.endswith("}"):
        expression = value[2:-1]
        key, _, default = expression.partition(":-")
        return os.getenv(key, default)
    return value


if __name__ == "__main__":
    main()
