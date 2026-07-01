from __future__ import annotations

from typing import Any

import pandas as pd

from strategy.risk_control import apply_risk_rules


def score_stock(name: str, symbol: str, df: pd.DataFrame, market_score: int | None = None) -> dict[str, Any]:
    if df.empty:
        return _empty_score(name, symbol, "个股无行情数据")

    latest = df.iloc[-1].to_dict()
    previous = df.iloc[-2].to_dict() if len(df) > 1 else latest
    score = 45
    reasons: list[str] = []

    close = float(latest.get("close", 0) or 0)
    prev_close = float(previous.get("close", close) or close)
    ma5 = float(latest.get("ma5", 0) or 0)
    ma10 = float(latest.get("ma10", 0) or 0)
    ma20 = float(latest.get("ma20", 0) or 0)
    ma60 = float(latest.get("ma60", 0) or 0)
    rsi = float(latest.get("rsi", 50) or 50)
    macd_hist = float(latest.get("macd_hist", 0) or 0)
    volume_change = float(latest.get("volume_change_pct", 0) or 0)

    if close > ma5:
        score += 5
        reasons.append("收盘价站上 MA5")
    if close > ma10:
        score += 6
        reasons.append("收盘价站上 MA10")
    if close > ma20:
        score += 10
        reasons.append("收盘价站上 MA20")
    if close > ma60:
        score += 12
        reasons.append("收盘价站上 MA60")
    if ma5 > ma10 > ma20:
        score += 8
        reasons.append("均线呈多头排列")
    if 40 <= rsi <= 70:
        score += 6
        reasons.append("RSI 未明显过热或过冷")
    elif rsi > 78:
        score -= 8
        reasons.append("RSI 过热")
    elif rsi < 32:
        score -= 8
        reasons.append("RSI 偏弱")
    if macd_hist > 0:
        score += 7
        reasons.append("MACD 动能为正")
    if prev_close and close > prev_close and volume_change > 0:
        score += 6
        reasons.append("放量上涨")
    elif prev_close and close < prev_close and volume_change > 20:
        score -= 8
        reasons.append("放量下跌")

    risk = apply_risk_rules(score, latest, market_score=market_score)
    return {
        "name": name,
        "symbol": symbol,
        "type": "stock",
        "score": risk["score"],
        "recommendation": risk["recommendation"],
        "risk_level": risk["risk_level"],
        "risk_flags": risk["flags"],
        "reasons": reasons,
        "latest": _compact_latest(latest),
    }


def _empty_score(name: str, symbol: str, reason: str) -> dict[str, Any]:
    return {
        "name": name,
        "symbol": symbol,
        "type": "stock",
        "score": 0,
        "recommendation": "无数据",
        "risk_level": "unknown",
        "risk_flags": [reason],
        "reasons": [],
        "latest": {},
    }


def _compact_latest(latest: dict[str, Any]) -> dict[str, Any]:
    keys = ["date", "close", "ma5", "ma10", "ma20", "ma60", "rsi", "macd_hist", "volume_change_pct"]
    return {key: latest.get(key) for key in keys}
