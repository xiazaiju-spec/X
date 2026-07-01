from __future__ import annotations

from datetime import date

import pandas as pd

from data_provider.base import MarketDataProvider, normalize_ohlcv


class AKShareProvider(MarketDataProvider):
    """AKShare provider for A-share, China indices, and selected HK fallbacks."""

    def fetch_daily(self, symbol: str, start: date, end: date) -> pd.DataFrame:
        import akshare as ak

        start_text = start.strftime("%Y%m%d")
        end_text = end.strftime("%Y%m%d")

        if self._looks_like_hk_index(symbol):
            return self._fetch_hk_index(ak, symbol, start, end)

        if self._looks_like_hk_stock(symbol):
            return self._fetch_hk_stock(ak, symbol, start, end)

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

    @staticmethod
    def _looks_like_hk_stock(symbol: str) -> bool:
        return symbol.endswith(".HK") or (symbol.isdigit() and len(symbol) == 5)

    @staticmethod
    def _looks_like_hk_index(symbol: str) -> bool:
        return symbol in {"^HSI", "HSI", "^HSTECH", "HSTECH"}

    @staticmethod
    def _fetch_hk_stock(ak: object, symbol: str, start: date, end: date) -> pd.DataFrame:
        code = symbol.replace(".HK", "").zfill(5)
        raw = ak.stock_hk_hist(
            symbol=code,
            period="daily",
            start_date=start.strftime("%Y%m%d"),
            end_date=end.strftime("%Y%m%d"),
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
    def _fetch_hk_index(ak: object, symbol: str, start: date, end: date) -> pd.DataFrame:
        code = symbol.replace("^", "")
        raw = ak.stock_hk_index_daily_sina(symbol=code)
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
