from __future__ import annotations

from datetime import date
from io import StringIO

import pandas as pd
import requests

from data_provider.base import MarketDataProvider, normalize_ohlcv


STOOQ_SYMBOL_MAP = {
    "^GSPC": "^spx",
    "^IXIC": "^ixic",
    "^DJI": "^dji",
    "AAPL": "aapl.us",
    "MSFT": "msft.us",
    "GOOGL": "googl.us",
    "GOOG": "goog.us",
    "AMZN": "amzn.us",
    "META": "meta.us",
    "NVDA": "nvda.us",
    "TSLA": "tsla.us",
}


class StooqProvider(MarketDataProvider):
    """Stooq CSV provider used as a no-key fallback for US market data."""

    def fetch_daily(self, symbol: str, start: date, end: date) -> pd.DataFrame:
        stooq_symbol = self._to_stooq_symbol(symbol)
        response = requests.get(
            "https://stooq.com/q/d/l/",
            params={
                "s": stooq_symbol,
                "d1": start.strftime("%Y%m%d"),
                "d2": end.strftime("%Y%m%d"),
                "i": "d",
            },
            headers={"User-Agent": "ai-stock-dashboard/0.1"},
            timeout=20,
        )
        response.raise_for_status()

        text = response.text.strip()
        if not text or text.lower().startswith("no data"):
            return normalize_ohlcv(pd.DataFrame())

        raw = pd.read_csv(StringIO(text))
        raw = raw.rename(
            columns={
                "Date": "date",
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Volume": "volume",
            }
        )
        return normalize_ohlcv(raw)

    @staticmethod
    def _to_stooq_symbol(symbol: str) -> str:
        if symbol in STOOQ_SYMBOL_MAP:
            return STOOQ_SYMBOL_MAP[symbol]
        if symbol.endswith(".HK"):
            return symbol.lower()
        if "." not in symbol and not symbol.startswith("^"):
            return f"{symbol.lower()}.us"
        return symbol.lower()
