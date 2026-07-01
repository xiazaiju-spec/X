from __future__ import annotations

from typing import Any

import pandas as pd

from strategy.risk_control import apply_risk_rules


def score_index(name: str, symbol: str, df: pd.DataFrame) -> dict[str, Any]:
    if df.empty:
        return _empty_score(name, symbol, "指数无行情数据")

    latest = df.iloc[-1].to_dict()
    previous = df.iloc[-2].to_dict() if len(df) > 1 else latest
    score = 50
    reasons: list[str] = []

    close = float(latest.get("close", 0) or 0)
    prev_close = float(previous.get("close", close) or close)
    ma5 = float(latest.get("ma5", 0) or 0)
    ma10 = float(latest.get("ma10", 0) or 0)
    ma20 = float(latest.get("ma20", 0) or 0)
    ma60 = float(latest.get("ma60", 0) or 0)
    rsi = float(latest.get("rsi", 50) or 50)
    macd_hist = float(latest.get("macd_hist", 0) or 0)

    if close > ma5:
        score += 6
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
        reasons.append("短中期均线多头排列")
    if 45 <= rsi <= 68:
        score += 6
        reasons.append("RSI 位于健康区间")
    elif rsi > 75:
        score -= 8
        reasons.append("RSI 偏高，短线过热")
    elif rsi < 35:
        score -= 8
        reasons.append("RSI 偏弱")
    if macd_hist > 0:
        score += 7
        reasons.append("MACD 柱线为正")
    if prev_close and close > prev_close:
        score += 5
        reasons.append("日线收涨")

    risk = apply_risk_rules(score, latest)
    return {
        "name": name,
        "symbol": symbol,
        "type": "index",
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
        "type": "index",
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
