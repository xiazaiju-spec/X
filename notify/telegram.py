from __future__ import annotations

import os

import requests


def send_telegram_message(markdown: str) -> None:
    enabled = os.getenv("TELEGRAM_ENABLED", "false").lower() == "true"
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not enabled:
        return
    if not token or not chat_id:
        raise ValueError("Telegram 已启用，但 TELEGRAM_BOT_TOKEN 或 TELEGRAM_CHAT_ID 未配置")

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    chunks = _chunk_text(markdown, 3800)
    for chunk in chunks:
        response = requests.post(
            url,
            json={"chat_id": chat_id, "text": chunk, "parse_mode": "Markdown"},
            timeout=20,
        )
        response.raise_for_status()


def _chunk_text(text: str, size: int) -> list[str]:
    return [text[i : i + size] for i in range(0, len(text), size)] or [""]
