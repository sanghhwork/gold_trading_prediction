"""
Gold Predictor - Technical Indicators
Tính toán các chỉ báo kỹ thuật cho giá vàng sử dụng thư viện `ta`.

Indicators:
- Trend: SMA(20,50,200), EMA(12,26)
- Momentum: RSI(14), MACD(12,26,9), Stochastic(14,3), Williams %R(14)
- Volatility: Bollinger Bands(20,2), ATR(14)
- Volume: OBV

Điểm mở rộng tương lai:
- Thêm Ichimoku Cloud
- Thêm Fibonacci Retracement levels
- Thêm custom indicators
"""

import pandas as pd
import numpy as np
import ta

from app.utils.constants import (
    SMA_PERIODS, EMA_PERIODS, RSI_PERIOD,
    MACD_FAST, MACD_SLOW, MACD_SIGNAL,
    BB_PERIOD, BB_STD, ATR_PERIOD,
    STOCH_K_PERIOD, STOCH_D_PERIOD, WILLIAMS_PERIOD,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


def add_all_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Thêm tất cả technical indicators vào DataFrame.

    Input: DataFrame có columns [date, open, high, low, close, volume]
    Output: DataFrame gốc + thêm ~25 columns indicators
    """
    logger.info(f"Tính technical indicators cho {len(df)} rows...")

    df = df.copy()
    df = df.sort_values("date").reset_index(drop=True)

    # Đảm bảo columns tồn tại (một số datasets không có volume)
    if "volume" not in df.columns:
        df["volume"] = 0

    # ===== TREND INDICATORS =====
    df = _add_moving_averages(df)

    # ===== MOMENTUM INDICATORS =====
    df = _add_rsi(df)
    df = _add_macd(df)
    df = _add_stochastic(df)
    df = _add_williams_r(df)

    # ===== VOLATILITY INDICATORS =====
    df = _add_bollinger_bands(df)
    df = _add_atr(df)

    # ===== VOLUME INDICATORS =====
    df = _add_obv(df)

    # ===== DERIVED SIGNALS =====
    df = _add_crossover_signals(df)

    indicator_cols = [c for c in df.columns if c not in ["date", "open", "high", "low", "close", "volume", "source"]]
    logger.info(f"Đã thêm {len(indicator_cols)} technical indicators")
    return df


# ===== TREND =====

def _add_moving_averages(df: pd.DataFrame) -> pd.DataFrame:
    """SMA và EMA."""
    for period in SMA_PERIODS:
        df[f"sma_{period}"] = ta.trend.sma_indicator(df["close"], window=period)

    for period in EMA_PERIODS:
        df[f"ema_{period}"] = ta.trend.ema_indicator(df["close"], window=period)

    # Price relative to SMAs (%)
    for period in SMA_PERIODS:
        col = f"sma_{period}"
        if col in df.columns:
            df[f"price_to_sma_{period}"] = (df["close"] - df[col]) / df[col] * 100

    return df


# ===== MOMENTUM =====

def _add_rsi(df: pd.DataFrame) -> pd.DataFrame:
    """RSI (Relative Strength Index)."""
    df["rsi"] = ta.momentum.rsi(df["close"], window=RSI_PERIOD)
    return df


def _add_macd(df: pd.DataFrame) -> pd.DataFrame:
    """MACD (Moving Average Convergence Divergence)."""
    macd = ta.trend.MACD(
        df["close"],
        window_fast=MACD_FAST,
        window_slow=MACD_SLOW,
        window_sign=MACD_SIGNAL,
    )
    df["macd"] = macd.macd()
    df["macd_signal"] = macd.macd_signal()
    df["macd_histogram"] = macd.macd_diff()
    return df


def _add_stochastic(df: pd.DataFrame) -> pd.DataFrame:
    """Stochastic Oscillator."""
    stoch = ta.momentum.StochasticOscillator(
        high=df["high"],
        low=df["low"],
        close=df["close"],
        window=STOCH_K_PERIOD,
        smooth_window=STOCH_D_PERIOD,
    )
    df["stoch_k"] = stoch.stoch()
    df["stoch_d"] = stoch.stoch_signal()
    return df


def _add_williams_r(df: pd.DataFrame) -> pd.DataFrame:
    """Williams %R."""
    df["williams_r"] = ta.momentum.williams_r(
        high=df["high"],
        low=df["low"],
        close=df["close"],
        lbp=WILLIAMS_PERIOD,
    )
    return df


# ===== VOLATILITY =====

def _add_bollinger_bands(df: pd.DataFrame) -> pd.DataFrame:
    """Bollinger Bands."""
    bb = ta.volatility.BollingerBands(
        close=df["close"],
        window=BB_PERIOD,
        window_dev=BB_STD,
    )
    df["bb_upper"] = bb.bollinger_hband()
    df["bb_middle"] = bb.bollinger_mavg()
    df["bb_lower"] = bb.bollinger_lband()
    df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / df["bb_middle"] * 100
    df["bb_position"] = (df["close"] - df["bb_lower"]) / (df["bb_upper"] - df["bb_lower"])
    return df


def _add_atr(df: pd.DataFrame) -> pd.DataFrame:
    """ATR (Average True Range)."""
    df["atr"] = ta.volatility.average_true_range(
        high=df["high"],
        low=df["low"],
        close=df["close"],
        window=ATR_PERIOD,
    )
    # ATR as percentage of close price
    df["atr_pct"] = df["atr"] / df["close"] * 100
    return df


# ===== VOLUME =====

def _add_obv(df: pd.DataFrame) -> pd.DataFrame:
    """OBV (On-Balance Volume)."""
    if df["volume"].sum() > 0:
        df["obv"] = ta.volume.on_balance_volume(df["close"], df["volume"])
    else:
        df["obv"] = 0
    return df


# ===== DERIVED SIGNALS =====

def _add_crossover_signals(df: pd.DataFrame) -> pd.DataFrame:
    """Thêm tín hiệu crossover (golden cross, death cross, etc.)."""
    # Golden Cross / Death Cross: SMA 50 vs SMA 200
    if "sma_50" in df.columns and "sma_200" in df.columns:
        df["sma_50_above_200"] = (df["sma_50"] > df["sma_200"]).astype(int)

    # MACD crossover
    if "macd" in df.columns and "macd_signal" in df.columns:
        df["macd_above_signal"] = (df["macd"] > df["macd_signal"]).astype(int)

    # RSI overbought/oversold zones
    if "rsi" in df.columns:
        df["rsi_overbought"] = (df["rsi"] > 70).astype(int)
        df["rsi_oversold"] = (df["rsi"] < 30).astype(int)

    return df
