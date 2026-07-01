from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

import pandas as pd


class MarketDataProvider(ABC):
    """Base interface for daily OHLCV market data providers."""

    @abstractmethod
    def fetch_daily(self, symbol: str, start: date, end: date) -> pd.DataFrame:
        """Return daily OHLCV data with columns: date, open, high, low, close, volume."""


REQUIRED_COLUMNS = ["date", "open", "high", "low", "close", "volume"]


def normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=REQUIRED_COLUMNS)

    normalized = df.copy()
    normalized["date"] = pd.to_datetime(normalized["date"]).dt.date

    for column in ["open", "high", "low", "close", "volume"]:
        normalized[column] = pd.to_numeric(normalized[column], errors="coerce")

    normalized = normalized.dropna(subset=["date", "close"])
    normalized = normalized.sort_values("date").reset_index(drop=True)
    return normalized[REQUIRED_COLUMNS]
