from __future__ import annotations

import os
from typing import Any

from ai.prompts import SYSTEM_PROMPT, build_report_prompt
from report.markdown_report import build_fallback_markdown_report


class LLMClient:
    def __init__(self) -> None:
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.base_url = os.getenv("OPENAI_BASE_URL") or None
        self.model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

    def generate_report(self, payload: dict[str, Any]) -> str:
        if not self.api_key:
            return build_fallback_markdown_report(payload, note="未配置 OPENAI_API_KEY，已生成本地 Markdown 报告。")

        try:
            from openai import OpenAI

            client = OpenAI(api_key=self.api_key, base_url=self.base_url)
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": build_report_prompt(payload)},
                ],
                temperature=0.2,
            )
            return response.choices[0].message.content or build_fallback_markdown_report(payload)
        except Exception as exc:
            return build_fallback_markdown_report(payload, note=f"大模型调用失败，已生成本地报告：{exc}")
