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
            provider = providers[item["provider"]]
            df = provider.fetch_daily(item["symbol"], start, end)
            df = add_technical_indicators(df)
            results.append(score_index(item["name"], item["symbol"], df))
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
            provider = providers[item["provider"]]
            df = provider.fetch_daily(item["symbol"], start, end)
            df = add_technical_indicators(df)
            market_score = market_score_by_market.get(item.get("market"))
            results.append(score_stock(item["name"], item["symbol"], df, market_score=market_score))
        except Exception as exc:
            results.append(error_score(item, "stock", exc))
    return results


def build_providers() -> dict[str, MarketDataProvider]:
    return {
        "akshare": AKShareProvider(),
        "yfinance": YFinanceProvider(),
    }


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
