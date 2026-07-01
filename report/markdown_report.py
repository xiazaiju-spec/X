from __future__ import annotations

from pathlib import Path
from typing import Any


def build_fallback_markdown_report(payload: dict[str, Any], note: str | None = None) -> str:
    lines = [
        f"# AI 股票决策日报 - {payload.get('run_date')}",
        "",
    ]
    if note:
        lines.extend([f"> {note}", ""])

    lines.extend(["## 市场指数评分", "", "| 指数 | 代码 | 评分 | 建议 | 风险 |", "|---|---:|---:|---|---|"])
    for item in payload.get("indices", []):
        lines.append(
            f"| {item['name']} | {item['symbol']} | {item['score']} | {item['recommendation']} | {item['risk_level']} |"
        )

    lines.extend(["", "## 自选股评分", "", "| 股票 | 代码 | 评分 | 建议 | 风险 |", "|---|---:|---:|---|---|"])
    for item in payload.get("stocks", []):
        lines.append(
            f"| {item['name']} | {item['symbol']} | {item['score']} | {item['recommendation']} | {item['risk_level']} |"
        )

    lines.extend(["", "## 风险提示", ""])
    flags = []
    for item in payload.get("indices", []) + payload.get("stocks", []):
        for flag in item.get("risk_flags", []):
            flags.append(f"- {item['name']}: {flag}")
    lines.extend(flags or ["- 暂无触发的高优先级风控规则。"])

    lines.extend(
        [
            "",
            "## 免责声明",
            "",
            "本报告仅用于个人研究和决策辅助，不构成任何投资建议。市场有风险，投资需谨慎。",
        ]
    )
    return "\n".join(lines)


def save_markdown_report(report_dir: str | Path, run_date: str, content: str) -> Path:
    directory = Path(report_dir)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"report-{run_date}.md"
    path.write_text(content, encoding="utf-8")
    return path
