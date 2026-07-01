from __future__ import annotations

from typing import Any


def print_console_summary(payload: dict[str, Any]) -> None:
    print("\nAI Stock Dashboard")
    print(f"Run date: {payload.get('run_date')}")
    print("\nIndices:")
    for item in payload.get("indices", []):
        print(f"- {item['name']}({item['symbol']}): {item['score']} / 100, {item['recommendation']}")
    print("\nStocks:")
    for item in payload.get("stocks", []):
        print(f"- {item['name']}({item['symbol']}): {item['score']} / 100, {item['recommendation']}")
