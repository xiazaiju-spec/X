from __future__ import annotations

import os
import importlib
from datetime import date
from decimal import Decimal
from typing import Any

import pandas as pd

from data_provider.base import MarketDataProvider, normalize_ohlcv


SYMBOL_MAP = {
    "^HSI": "HSI.HK",
    "^HSTECH": "HSTECH.HK",
    "^GSPC": "SPX.US",
    "^IXIC": "IXIC.US",
    "0700.HK": "700.HK",
}


class LongbridgeProvider(MarketDataProvider):
    """Longbridge OpenAPI quote-only provider.

    The first version intentionally does not expose trading operations.
    """

    def __init__(self) -> None:
        self.trade_enabled = os.getenv("LONGBRIDGE_TRADE_ENABLED", "false").lower() == "true"
        self._config = None
        self._quote_ctx = None
        self._sdk = None
        self._init_error: str | None = None
        self._initialize()

    def fetch_daily(self, symbol: str, start: date, end: date) -> pd.DataFrame:
        return self.get_history_kline(symbol, start, end)

    def get_basic_quote(self, symbols: list[str]) -> list[Any]:
        return self.get_realtime_quote(symbols)

    def get_realtime_quote(self, symbols: list[str]) -> pd.DataFrame:
        ctx = self._require_quote_context()
        normalized = [self.normalize_symbol(symbol) for symbol in symbols]
        quotes = ctx.quote(normalized)
        rows = []
        for quote in quotes:
            rows.append(
                {
                    "symbol": getattr(quote, "symbol", None),
                    "last_done": _to_float(getattr(quote, "last_done", None)),
                    "prev_close": _to_float(getattr(quote, "prev_close", None)),
                    "open": _to_float(getattr(quote, "open", None)),
                    "high": _to_float(getattr(quote, "high", None)),
                    "low": _to_float(getattr(quote, "low", None)),
                    "volume": _to_float(getattr(quote, "volume", None)),
                    "timestamp": getattr(quote, "timestamp", None),
                    "trade_status": str(getattr(quote, "trade_status", "")),
                }
            )
        return pd.DataFrame(rows)

    def get_history_kline(self, symbol: str, start: date, end: date) -> pd.DataFrame:
        ctx = self._require_quote_context()
        sdk = self._require_sdk()
        lb_symbol = self.normalize_symbol(symbol)
        args = [
            lb_symbol,
            sdk.Period.Day,
            sdk.AdjustType.ForwardAdjust,
            start,
            end,
        ]
        trade_sessions = getattr(getattr(sdk, "TradeSessions", None), "Intraday", None)
        if trade_sessions is not None:
            try:
                candles = ctx.history_candlesticks_by_date(*args, trade_sessions)
            except TypeError:
                candles = ctx.history_candlesticks_by_date(*args)
        else:
            candles = ctx.history_candlesticks_by_date(*args)
        return self._candlesticks_to_dataframe(candles)

    @staticmethod
    def normalize_symbol(symbol: str) -> str:
        if symbol in SYMBOL_MAP:
            return SYMBOL_MAP[symbol]
        if symbol.endswith(".HK"):
            return f"{int(symbol[:-3])}.HK" if symbol[:-3].isdigit() else symbol
        if symbol.endswith(".US"):
            return symbol
        if symbol.isalpha():
            return f"{symbol.upper()}.US"
        return symbol

    def _initialize(self) -> None:
        missing = [
            key
            for key in ["LONGBRIDGE_APP_KEY", "LONGBRIDGE_APP_SECRET", "LONGBRIDGE_ACCESS_TOKEN"]
            if not os.getenv(key)
        ]
        if missing:
            self._init_error = "missing env: " + ", ".join(missing)
            return

        try:
            sdk = importlib.import_module("longbridge.openapi")
            self._sdk = sdk
            self._config = sdk.Config.from_apikey_env()
            self._quote_ctx = sdk.QuoteContext(self._config)
        except Exception as exc:
            self._init_error = f"Longbridge SDK init failed: {exc}"

    def _require_quote_context(self) -> Any:
        if self._quote_ctx is None:
            raise RuntimeError(self._init_error or "Longbridge quote context is not initialized")
        return self._quote_ctx

    def _require_sdk(self) -> Any:
        if self._sdk is None:
            raise RuntimeError(self._init_error or "Longbridge SDK is not initialized")
        return self._sdk

    @staticmethod
    def _candlesticks_to_dataframe(candles: list[Any]) -> pd.DataFrame:
        rows = []
        for candle in candles:
            rows.append(
                {
                    "date": getattr(candle, "timestamp", None),
                    "open": _to_float(getattr(candle, "open", None)),
                    "high": _to_float(getattr(candle, "high", None)),
                    "low": _to_float(getattr(candle, "low", None)),
                    "close": _to_float(getattr(candle, "close", None)),
                    "volume": _to_float(getattr(candle, "volume", None)),
                }
            )
        return normalize_ohlcv(pd.DataFrame(rows))


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
