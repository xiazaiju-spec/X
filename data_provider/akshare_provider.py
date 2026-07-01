from __future__ import annotations

from datetime import date

import pandas as pd

from data_provider.base import MarketDataProvider, normalize_ohlcv


class AKShareProvider(MarketDataProvider):
    """AKShare provider for A-share stocks and mainland China indices."""

    def fetch_daily(self, symbol: str, start: date, end: date) -> pd.DataFrame:
        import akshare as ak

        start_text = start.strftime("%Y%m%d")
        end_text = end.strftime("%Y%m%d")

        if self._looks_like_cn_index(symbol):
            raw = ak.stock_zh_index_daily(symbol=symbol)
            raw = raw.rename(
                columns={
                    "date": "date",
                    "open": "open",
                    "high": "high",
                    "low": "low",
                    "close": "close",
                    "volume": "volume",
                }
            )
            raw["date"] = pd.to_datetime(raw["date"]).dt.date
            raw = raw[(raw["date"] >= start) & (raw["date"] <= end)]
            return normalize_ohlcv(raw)

        raw = ak.stock_zh_a_hist(
            symbol=symbol,
            period="daily",
            start_date=start_text,
            end_date=end_text,
            adjust="qfq",
        )
        raw = raw.rename(
            columns={
                "日期": "date",
                "开盘": "open",
                "最高": "high",
                "最低": "low",
                "收盘": "close",
                "成交量": "volume",
            }
        )
        return normalize_ohlcv(raw)

    @staticmethod
    def _looks_like_cn_index(symbol: str) -> bool:
        return symbol.startswith(("sh", "sz")) and len(symbol) == 8
