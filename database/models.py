from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ScoreRecord:
    run_date: str
    asset_type: str
    name: str
    symbol: str
    score: int
    recommendation: str
    risk_level: str
    payload: dict[str, Any]
