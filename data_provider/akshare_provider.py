from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd

from data_provider.base import MarketDataProvider, normalize_ohlcv


CN_DATE = "\u65e5\u671f"
CN_OPEN = "\u5f00\u76d8"
CN_HIGH = "\u6700\u9ad8"
CN_LOW = "\u6700\u4f4e"
CN_CLOSE = "\u6536\u76d8"
CN_VOLUME = "\u6210\u4ea4\u91cf"


class AKShareProvider(MarketDataProvider):
    """AKShare provider for A-share, China indices, HK, and US stock fallbacks."""

    def fetch_daily(self, symbol: str, start: date, end: date) -> pd.DataFrame:
        import akshare as ak

        if self._looks_like_hk_index(symbol):
            return self._fetch_hk_index(ak, symbol, start, end)

        if self._looks_like_hk_stock(symbol):
            return self._fetch_hk_stock(ak, symbol, start, end)

        if self._looks_like_cn_index(symbol):
            return self._fetch_cn_index(ak, symbol, start, end)

        if self._looks_like_us_stock(symbol):
            return self._fetch_us_stock(ak, symbol, start, end)

        return self._fetch_cn_stock(ak, symbol, start, end)

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
    def _looks_like_us_stock(symbol: str) -> bool:
        return symbol.isalpha() or symbol.lower().endswith(".us")

    def _fetch_cn_stock(self, ak: Any, symbol: str, start: date, end: date) -> pd.DataFrame:
        errors = []
        start_text = start.strftime("%Y%m%d")
        end_text = end.strftime("%Y%m%d")

        try:
            raw = ak.stock_zh_a_hist(
                symbol=symbol,
                period="daily",
                start_date=start_text,
                end_date=end_text,
                adjust="qfq",
            )
            return normalize_ohlcv(_rename_ohlcv_columns(raw))
        except Exception as exc:
            errors.append(f"stock_zh_a_hist: {exc}")

        try:
            sina_symbol = _cn_sina_symbol(symbol)
            raw = ak.stock_zh_a_daily(symbol=sina_symbol, start_date=start_text, end_date=end_text, adjust="qfq")
            return normalize_ohlcv(_rename_ohlcv_columns(raw))
        except Exception as exc:
            errors.append(f"stock_zh_a_daily: {exc}")

        raise RuntimeError("AKShare CN stock failed: " + " | ".join(errors))

    @staticmethod
    def _fetch_cn_index(ak: Any, symbol: str, start: date, end: date) -> pd.DataFrame:
        raw = ak.stock_zh_index_daily(symbol=symbol)
        raw = _rename_ohlcv_columns(raw)
        raw["date"] = pd.to_datetime(raw["date"]).dt.date
        raw = raw[(raw["date"] >= start) & (raw["date"] <= end)]
        return normalize_ohlcv(raw)

    @staticmethod
    def _fetch_hk_stock(ak: Any, symbol: str, start: date, end: date) -> pd.DataFrame:
        code = symbol.replace(".HK", "").zfill(5)
        raw = ak.stock_hk_hist(
            symbol=code,
            period="daily",
            start_date=start.strftime("%Y%m%d"),
            end_date=end.strftime("%Y%m%d"),
            adjust="qfq",
        )
        return normalize_ohlcv(_rename_ohlcv_columns(raw))

    @staticmethod
    def _fetch_hk_index(ak: Any, symbol: str, start: date, end: date) -> pd.DataFrame:
        code = symbol.replace("^", "")
        raw = ak.stock_hk_index_daily_sina(symbol=code)
        raw = _rename_ohlcv_columns(raw)
        raw["date"] = pd.to_datetime(raw["date"]).dt.date
        raw = raw[(raw["date"] >= start) & (raw["date"] <= end)]
        return normalize_ohlcv(raw)

    @staticmethod
    def _fetch_us_stock(ak: Any, symbol: str, start: date, end: date) -> pd.DataFrame:
        errors = []
        code = symbol.replace(".US", "").replace(".us", "").upper()

        try:
            raw = ak.stock_us_daily(symbol=code, adjust="qfq")
            raw = _rename_ohlcv_columns(raw)
            raw["date"] = pd.to_datetime(raw["date"]).dt.date
            raw = raw[(raw["date"] >= start) & (raw["date"] <= end)]
            return normalize_ohlcv(raw)
        except Exception as exc:
            errors.append(f"stock_us_daily: {exc}")

        try:
            em_symbol = _lookup_us_em_symbol(ak, code)
            raw = ak.stock_us_hist(
                symbol=em_symbol,
                period="daily",
                start_date=start.strftime("%Y%m%d"),
                end_date=end.strftime("%Y%m%d"),
                adjust="qfq",
            )
            return normalize_ohlcv(_rename_ohlcv_columns(raw))
        except Exception as exc:
            errors.append(f"stock_us_hist: {exc}")

        raise RuntimeError("AKShare US stock failed: " + " | ".join(errors))


def _rename_ohlcv_columns(raw: pd.DataFrame) -> pd.DataFrame:
    return raw.rename(
        columns={
            CN_DATE: "date",
            CN_OPEN: "open",
            CN_HIGH: "high",
            CN_LOW: "low",
            CN_CLOSE: "close",
            CN_VOLUME: "volume",
            "date": "date",
            "open": "open",
            "high": "high",
            "low": "low",
            "close": "close",
            "volume": "volume",
            "Date": "date",
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume",
        }
    )


def _cn_sina_symbol(symbol: str) -> str:
    if symbol.startswith(("sh", "sz")):
        return symbol
    return f"sh{symbol}" if symbol.startswith(("5", "6", "9")) else f"sz{symbol}"


def _lookup_us_em_symbol(ak: Any, code: str) -> str:
    spot = ak.stock_us_spot_em()
    code_col = CN_CODE = "\u4ee3\u7801"
    if code_col not in spot.columns:
        code_col = "代码"
    matches = spot[spot[code_col].astype(str).str.upper().str.endswith(f".{code}")]
    if matches.empty:
        raise ValueError(f"cannot find Eastmoney US symbol for {code}")
    return str(matches.iloc[0][code_col])
