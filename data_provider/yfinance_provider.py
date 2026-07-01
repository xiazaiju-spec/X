from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

from data_provider.base import MarketDataProvider, normalize_ohlcv


class YFinanceProvider(MarketDataProvider):
    """Yahoo Finance provider for Hong Kong, US, and global tickers."""

    def fetch_daily(self, symbol: str, start: date, end: date) -> pd.DataFrame:
        import yfinance as yf

        raw = yf.download(
            symbol,
            start=start.isoformat(),
            end=(end + timedelta(days=1)).isoformat(),
            interval="1d",
            auto_adjust=False,
            progress=False,
            threads=False,
        )
        if raw.empty:
            return normalize_ohlcv(pd.DataFrame())

        if isinstance(raw.columns, pd.MultiIndex):
            raw.columns = raw.columns.get_level_values(0)

        raw = raw.reset_index().rename(
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
