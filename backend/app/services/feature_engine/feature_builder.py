"""
Gold Predictor - Feature Builder Pipeline
Orchestrate toàn bộ quá trình tạo feature matrix cho ML models.

Pipeline: Load data → Technical Indicators → Macro Features →
          Calendar Features → Lag Features → Returns → Target → Clean

Điểm mở rộng tương lai:
- Thêm feature selection (mutual information, correlation filter)
- Thêm feature importance tracking
- Thêm auto feature engineering (featuretools)
"""

from datetime import date
from typing import Optional

import pandas as pd
import numpy as np
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.database import get_session_factory
from app.db.models import GoldPrice, MacroIndicator
from app.services.feature_engine.technical_indicators import add_all_technical_indicators
from app.services.feature_engine.macro_features import add_macro_features
from app.utils.constants import (
    LAG_DAYS, RETURN_PERIODS,
    TREND_THRESHOLD_UP, TREND_THRESHOLD_DOWN,
    PREDICTION_HORIZONS,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


class FeatureBuilder:
    """
    Build feature matrix cho ML models.

    Usage:
        builder = FeatureBuilder()
        df = builder.build_features()
        X, y = builder.get_train_data(df, target="close", horizon="7d")
    """

    def __init__(self):
        self.logger = get_logger("feature_builder")

    def build_features(
        self,
        source: str = "xau_usd",
        include_macro: bool = True,
    ) -> pd.DataFrame:
        """
        Build complete feature matrix.

        Args:
            source: "xau_usd" hoặc "sjc"
            include_macro: Có thêm macro features không

        Returns:
            DataFrame với tất cả features, sorted by date
        """
        self.logger.info(f"Building features cho {source}...")

        # 1. Load gold price data
        gold_df = self._load_gold_data(source)
        if gold_df.empty:
            self.logger.error("Không có gold data!")
            return pd.DataFrame()

        self.logger.info(f"Gold data: {len(gold_df)} rows ({gold_df['date'].min()} → {gold_df['date'].max()})")

        # 2. Technical Indicators
        df = add_all_technical_indicators(gold_df)

        # 3. Macro Features
        if include_macro:
            macro_df = self._load_macro_data()
            if not macro_df.empty:
                df = add_macro_features(df, macro_df)
            else:
                self.logger.warning("Không có macro data, skip macro features")

        # 4. Calendar Features
        df = self._add_calendar_features(df)

        # 5. Lag Features
        df = self._add_lag_features(df)

        # 6. Return Features
        df = self._add_return_features(df)

        # 7. Target Variables (cho training)
        df = self._add_target_variables(df)

        # 8. Clean
        df = self._clean_features(df)

        total_features = len([c for c in df.columns if c not in ["date", "source"]])
        self.logger.info(f"Feature matrix: {len(df)} rows × {total_features} features")

        return df

    def _load_gold_data(self, source: str) -> pd.DataFrame:
        """Load giá vàng từ DB."""
        SessionLocal = get_session_factory()
        db = SessionLocal()
        try:
            records = db.query(GoldPrice).filter_by(
                source=source
            ).order_by(GoldPrice.date).all()

            if not records:
                return pd.DataFrame()

            data = [{
                "date": r.date,
                "open": r.open,
                "high": r.high,
                "low": r.low,
                "close": r.close,
                "volume": r.volume or 0,
                "source": r.source,
            } for r in records]

            return pd.DataFrame(data)
        finally:
            db.close()

    def _load_macro_data(self) -> pd.DataFrame:
        """Load macro indicators từ DB."""
        SessionLocal = get_session_factory()
        db = SessionLocal()
        try:
            records = db.query(MacroIndicator).order_by(
                MacroIndicator.date
            ).all()

            if not records:
                return pd.DataFrame()

            data = [{
                "date": r.date,
                "indicator": r.indicator,
                "close": r.close,
            } for r in records]

            return pd.DataFrame(data)
        finally:
            db.close()

    def _add_calendar_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Thêm calendar features (seasonal patterns)."""
        df["date_dt"] = pd.to_datetime(df["date"])
        df["day_of_week"] = df["date_dt"].dt.dayofweek       # 0=Mon, 4=Fri
        df["month"] = df["date_dt"].dt.month                  # 1-12
        df["quarter"] = df["date_dt"].dt.quarter              # 1-4
        df["is_month_start"] = df["date_dt"].dt.is_month_start.astype(int)
        df["is_month_end"] = df["date_dt"].dt.is_month_end.astype(int)
        df["is_quarter_end"] = df["date_dt"].dt.is_quarter_end.astype(int)
        df["week_of_year"] = df["date_dt"].dt.isocalendar().week.astype(int)
        df = df.drop(columns=["date_dt"])

        self.logger.info("Đã thêm 7 calendar features")
        return df

    def _add_lag_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Thêm lag features (giá trị N ngày trước)."""
        for lag in LAG_DAYS:
            df[f"close_lag_{lag}d"] = df["close"].shift(lag)
            df[f"volume_lag_{lag}d"] = df["volume"].shift(lag)

            # High/Low lag
            df[f"high_lag_{lag}d"] = df["high"].shift(lag)
            df[f"low_lag_{lag}d"] = df["low"].shift(lag)

        # Rolling statistics
        for window in [5, 10, 20]:
            df[f"close_rolling_mean_{window}d"] = df["close"].rolling(window).mean()
            df[f"close_rolling_std_{window}d"] = df["close"].rolling(window).std()
            df[f"volume_rolling_mean_{window}d"] = df["volume"].rolling(window).mean()

            # Rolling max/min (support/resistance proxy)
            df[f"high_rolling_max_{window}d"] = df["high"].rolling(window).max()
            df[f"low_rolling_min_{window}d"] = df["low"].rolling(window).min()

        self.logger.info(f"Đã thêm lag features (lags: {LAG_DAYS})")
        return df

    def _add_return_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Thêm return features (% thay đổi giá)."""
        for period in RETURN_PERIODS:
            df[f"return_{period}d"] = df["close"].pct_change(period) * 100

        # Cumulative return
        df["cumulative_return_20d"] = (
            (df["close"] / df["close"].shift(20) - 1) * 100
        )

        # Volatility (rolling std of returns)
        df["volatility_5d"] = df["return_1d"].rolling(5).std() if "return_1d" in df.columns else 0
        df["volatility_20d"] = df["return_1d"].rolling(20).std() if "return_1d" in df.columns else 0

        self.logger.info(f"Đã thêm return features (periods: {RETURN_PERIODS})")
        return df

    def _add_target_variables(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Thêm target variables cho supervised learning.
        
        Targets:
        - target_price_{horizon}: Giá close N ngày tới (regression)
        - target_return_{horizon}: % return N ngày tới
        - target_trend_{horizon}: 0=Giảm, 1=Sideway, 2=Tăng (classification)
        """
        for name, days in PREDICTION_HORIZONS.items():
            # Price target (regression)
            df[f"target_price_{name}"] = df["close"].shift(-days)

            # Return target
            future_return = (df["close"].shift(-days) / df["close"] - 1)
            df[f"target_return_{name}"] = future_return * 100

            # Trend target (classification)
            df[f"target_trend_{name}"] = pd.cut(
                future_return,
                bins=[-np.inf, TREND_THRESHOLD_DOWN, TREND_THRESHOLD_UP, np.inf],
                labels=[0, 1, 2],  # Giảm, Sideway, Tăng
            ).astype(float)

        self.logger.info(f"Đã thêm target variables cho {list(PREDICTION_HORIZONS.keys())}")
        return df

    def _clean_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean up: drop rows with too many NaN, replace inf."""
        original_len = len(df)

        # Replace inf
        df = df.replace([np.inf, -np.inf], np.nan)

        # Drop rows where ALL features are NaN (except date/source)
        feature_cols = [c for c in df.columns if c not in ["date", "source"]]
        nan_threshold = len(feature_cols) * 0.5  # Drop if >50% NaN
        df = df.dropna(thresh=int(len(df.columns) - nan_threshold))

        dropped = original_len - len(df)
        if dropped > 0:
            self.logger.info(f"Cleaned: dropped {dropped} rows (>50% NaN)")

        return df

    def get_train_data(
        self,
        df: pd.DataFrame,
        horizon: str = "7d",
        feature_cols: Optional[list] = None,
    ) -> tuple[pd.DataFrame, pd.Series, pd.Series, pd.Series]:
        """
        Tách feature matrix thành X và multiple y targets.

        Returns:
            (X, y_price, y_trend, y_return)
        """
        # Exclude columns
        exclude_cols = {"date", "source"}
        target_cols = {c for c in df.columns if c.startswith("target_")}
        exclude_cols.update(target_cols)

        if feature_cols is None:
            feature_cols = [c for c in df.columns if c not in exclude_cols]

        # Drop rows with NaN target
        price_target = f"target_price_{horizon}"
        trend_target = f"target_trend_{horizon}"
        return_target = f"target_return_{horizon}"

        valid = df.dropna(subset=[price_target, trend_target])

        X = valid[feature_cols].copy()
        y_price = valid[price_target].copy()
        y_trend = valid[trend_target].astype(int).copy()
        y_return = valid[return_target].copy()

        # Fill remaining NaN in X with 0 (safeguard)
        X = X.fillna(0)

        self.logger.info(
            f"Train data: X={X.shape}, targets: "
            f"price={len(y_price)}, trend={len(y_trend)}, return={len(y_return)}"
        )

        return X, y_price, y_trend, y_return
