from __future__ import annotations

import numpy as np
import pandas as pd


def add_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    data = df.copy().sort_values("date").reset_index(drop=True)
    if data.empty:
        return data

    close = pd.to_numeric(data["close"], errors="coerce")
    volume = pd.to_numeric(data["volume"], errors="coerce")

    for window in [5, 10, 20, 60]:
        data[f"ma{window}"] = close.rolling(window=window, min_periods=1).mean()

    data["rsi"] = calculate_rsi(close)
    macd, macd_signal, macd_hist = calculate_macd(close)
    data["macd"] = macd
    data["macd_signal"] = macd_signal
    data["macd_hist"] = macd_hist
    data["volume_change_pct"] = volume.pct_change().replace([np.inf, -np.inf], np.nan) * 100
    return data


def calculate_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)


def calculate_macd(
    close: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd = ema_fast - ema_slow
    macd_signal = macd.ewm(span=signal, adjust=False).mean()
    macd_hist = macd - macd_signal
    return macd, macd_signal, macd_hist
