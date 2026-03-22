"""
Gold Predictor - Macro Features
Tính toán features từ macro indicators (DXY, Oil, USD/VND, Rates, S&P 500).

Features:
- % thay đổi hàng ngày của mỗi indicator
- Cross-asset ratios và correlations
- Moving averages của macro indicators
- Lag features

Điểm mở rộng tương lai:
- Thêm CPI change rate
- Thêm Fed rate decisions (event-based)
- Thêm rolling correlation windows
"""

import pandas as pd
import numpy as np

from app.utils.logger import get_logger

logger = get_logger(__name__)


def add_macro_features(
    gold_df: pd.DataFrame,
    macro_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Merge macro indicators vào gold DataFrame và tạo features.

    Args:
        gold_df: DataFrame giá vàng [date, open, high, low, close, volume]
        macro_df: DataFrame macro [date, indicator, close]

    Returns:
        gold_df với thêm macro feature columns
    """
    logger.info(f"Tính macro features: {len(gold_df)} gold rows, {len(macro_df)} macro rows")

    df = gold_df.copy()
    df = df.sort_values("date").reset_index(drop=True)

    # Pivot macro_df: mỗi indicator thành 1 cột
    if macro_df.empty:
        logger.warning("Không có macro data, skip macro features")
        return df

    macro_pivot = macro_df.pivot_table(
        index="date",
        columns="indicator",
        values="close",
        aggfunc="last",
    ).reset_index()

    # Merge với gold data (left join - giữ tất cả ngày gold)
    df = df.merge(macro_pivot, on="date", how="left")

    # Forward fill missing macro values (weekends/holidays)
    macro_cols = [c for c in macro_pivot.columns if c != "date"]
    for col in macro_cols:
        if col in df.columns:
            df[col] = df[col].ffill()

    # ===== Tạo features =====

    # 1. Daily % change cho mỗi macro indicator
    for col in macro_cols:
        if col in df.columns:
            df[f"{col}_change_1d"] = df[col].pct_change(1) * 100
            df[f"{col}_change_5d"] = df[col].pct_change(5) * 100

    # 2. Cross-asset ratios
    if "dxy" in df.columns:
        # Gold/DXY ratio - thường nghịch biến
        df["gold_dxy_ratio"] = df["close"] / df["dxy"]
        df["gold_dxy_ratio_change"] = df["gold_dxy_ratio"].pct_change() * 100

    if "oil_wti" in df.columns:
        # Gold/Oil ratio
        df["gold_oil_ratio"] = df["close"] / df["oil_wti"]

    if "us_10y" in df.columns:
        # Real yield proxy: 10Y yield level (higher = worse for gold)
        df["us_10y_level"] = df["us_10y"]

    if "usd_vnd" in df.columns:
        # USD/VND change affects VN gold price
        df["usd_vnd_change_1d"] = df["usd_vnd"].pct_change(1) * 100

    # 3. SMA of macro indicators (trend)
    for col in macro_cols:
        if col in df.columns:
            df[f"{col}_sma_20"] = df[col].rolling(window=20).mean()
            df[f"{col}_above_sma20"] = (df[col] > df[f"{col}_sma_20"]).astype(int)

    # 4. DXY momentum (key driver)
    if "dxy" in df.columns:
        df["dxy_rsi_14"] = _simple_rsi(df["dxy"], 14)

    count = len([c for c in df.columns if c not in gold_df.columns])
    logger.info(f"Đã thêm {count} macro features")
    return df


def _simple_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Simple RSI calculation without ta library (for macro indicators)."""
    delta = series.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))
