from __future__ import annotations

from typing import Any


def apply_risk_rules(score: int, latest: dict[str, Any], market_score: int | None = None) -> dict[str, Any]:
    adjusted = int(max(0, min(100, score)))
    flags: list[str] = []
    risk_level = "normal"

    close = float(latest.get("close", 0) or 0)
    ma20 = float(latest.get("ma20", 0) or 0)
    ma60 = float(latest.get("ma60", 0) or 0)

    if ma20 and close < ma20:
        adjusted -= 10
        flags.append("跌破 MA20，趋势转弱")

    if ma60 and close < ma60:
        adjusted -= 15
        risk_level = "high"
        flags.append("跌破 MA60，高风险")

    max_recommendation = None
    if market_score is not None and market_score < 45:
        max_recommendation = "轻仓观察"
        flags.append("指数评分低于 45，限制个股建议")

    adjusted = int(max(0, min(100, adjusted)))
    recommendation = score_to_recommendation(adjusted)
    if max_recommendation == "轻仓观察":
        recommendation = cap_recommendation(recommendation)

    return {
        "score": adjusted,
        "risk_level": risk_level,
        "flags": flags,
        "recommendation": recommendation,
    }


def score_to_recommendation(score: int) -> str:
    if score >= 80:
        return "积极关注"
    if score >= 65:
        return "逢低配置"
    if score >= 50:
        return "轻仓观察"
    if score >= 35:
        return "谨慎观望"
    return "回避"


def cap_recommendation(recommendation: str) -> str:
    rank = ["回避", "谨慎观望", "轻仓观察", "逢低配置", "积极关注"]
    return recommendation if rank.index(recommendation) <= rank.index("轻仓观察") else "轻仓观察"
