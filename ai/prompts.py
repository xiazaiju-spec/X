from __future__ import annotations

import json
from typing import Any


SYSTEM_PROMPT = """你是一名严谨的股票市场分析助手。请基于结构化评分、技术指标和风控规则生成中文 Markdown 报告。
要求：客观、克制、强调风险；不要承诺收益；不要编造不存在的数据。"""


def build_report_prompt(payload: dict[str, Any]) -> str:
    return (
        "请根据以下 JSON 数据生成每日股票决策报告，包含市场概览、指数评分、个股评分、风险提示和明日关注点。\n\n"
        f"```json\n{json.dumps(payload, ensure_ascii=False, default=str, indent=2)}\n```"
    )
