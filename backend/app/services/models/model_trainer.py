"""
Gold Predictor - Model Trainer
Orchestrate toàn bộ quá trình train, evaluate và save models.

Pipeline: Build Features → Split Data → Train Models → Evaluate → Ensemble → Save

Điểm mở rộng tương lai:
- Thêm walk-forward validation
- Thêm auto hyperparameter tuning
- Thêm model comparison dashboard
"""

from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.model_selection import TimeSeriesSplit

from app.services.feature_engine.feature_builder import FeatureBuilder
from app.services.models.xgboost_models import XGBoostPriceModel, XGBoostTrendModel
from app.services.models.ensemble_model import EnsemblePriceModel, EnsembleTrendModel
from app.utils.constants import PREDICTION_HORIZONS
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ModelTrainer:
    """
    Orchestrate model training pipeline.

    Usage:
        trainer = ModelTrainer()
        results = trainer.train_all(horizon="7d")
    """

    def __init__(self):
        self.logger = get_logger("model_trainer")
        self.feature_builder = FeatureBuilder()
        self.trained_models = {}

    def train_all(
        self,
        horizon: str = "7d",
        test_size: float = 0.2,
        source: str = "xau_usd",
    ) -> dict:
        """
        Train tất cả models cho 1 horizon.

        Returns:
            dict với model names và metrics
        """
        self.logger.info(f"{'='*60}")
        self.logger.info(f"TRAINING PIPELINE - Horizon: {horizon}")
        self.logger.info(f"{'='*60}")

        # 1. Build features
        self.logger.info("Step 1: Building features...")
        df = self.feature_builder.build_features(source=source, include_macro=True)
        if df.empty:
            self.logger.error("Feature matrix rong!")
            return {}

        # 2. Get train data
        X, y_price, y_trend, y_return = self.feature_builder.get_train_data(df, horizon=horizon)
        self.logger.info(f"Data shape: X={X.shape}")

        # 3. Time-series split (IMPORTANT: không shuffle!)
        split_idx = int(len(X) * (1 - test_size))
        X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
        y_price_train, y_price_test = y_price.iloc[:split_idx], y_price.iloc[split_idx:]
        y_trend_train, y_trend_test = y_trend.iloc[:split_idx], y_trend.iloc[split_idx:]

        self.logger.info(
            f"Train: {len(X_train)} samples, Test: {len(X_test)} samples, "
            f"Split ratio: {1-test_size:.0%}/{test_size:.0%}"
        )

        results = {}

        # 4. Train XGBoost Price Model
        self.logger.info("\nStep 4a: Training XGBoost Price...")
        xgb_price = XGBoostPriceModel(horizon=horizon)
        xgb_price.train(X_train, y_price_train, X_val=X_test, y_val=y_price_test)
        price_metrics = xgb_price.evaluate(X_test, y_price_test)
        results["xgboost_price"] = price_metrics

        # 5. Train XGBoost Trend Model
        self.logger.info("\nStep 4b: Training XGBoost Trend...")
        xgb_trend = XGBoostTrendModel(horizon=horizon)
        xgb_trend.train(X_train, y_trend_train, X_val=X_test, y_val=y_trend_test)
        trend_metrics = xgb_trend.evaluate(X_test, y_trend_test)
        results["xgboost_trend"] = trend_metrics

        # 6. Ensemble (dùng XGBoost models)
        self.logger.info("\nStep 5: Building Ensemble...")
        ensemble_price = EnsemblePriceModel(horizon=horizon)
        ensemble_price.add_model(xgb_price, weight=1.0)
        ensemble_price.train(X_train, y_price_train)

        ensemble_trend = EnsembleTrendModel(horizon=horizon)
        ensemble_trend.add_model(xgb_trend, weight=1.0)
        ensemble_trend.train(X_train, y_trend_train)

        # 7. Save models
        self.logger.info("\nStep 6: Saving models...")
        xgb_price.save()
        xgb_trend.save()
        ensemble_price.save()
        ensemble_trend.save()

        # Store for later use
        self.trained_models[horizon] = {
            "xgb_price": xgb_price,
            "xgb_trend": xgb_trend,
            "ensemble_price": ensemble_price,
            "ensemble_trend": ensemble_trend,
        }

        # Feature importance
        fi = xgb_price.get_feature_importance()
        if fi is not None:
            self.logger.info("\nTop 10 features (price model):")
            for _, row in fi.head(10).iterrows():
                self.logger.info(f"  {row['feature']}: {row['importance']:.4f}")

        # Summary
        self.logger.info(f"\n{'='*60}")
        self.logger.info("TRAINING SUMMARY:")
        self.logger.info(f"  XGBoost Price - MAE: {price_metrics['mae']:.2f}, "
                        f"RMSE: {price_metrics['rmse']:.2f}, R2: {price_metrics['r2']:.4f}")
        self.logger.info(f"  XGBoost Trend - Accuracy: {trend_metrics['accuracy']:.4f}, "
                        f"F1: {trend_metrics['f1_weighted']:.4f}")
        self.logger.info(f"{'='*60}")

        return results

    def train_all_horizons(self, source: str = "xau_usd") -> dict:
        """Train tất cả models cho tất cả horizons (1d, 7d, 30d)."""
        all_results = {}
        for horizon in PREDICTION_HORIZONS:
            self.logger.info(f"\n{'#'*60}")
            self.logger.info(f"# Training for horizon: {horizon}")
            self.logger.info(f"{'#'*60}")
            results = self.train_all(horizon=horizon, source=source)
            all_results[horizon] = results
        return all_results

    def predict(
        self,
        horizon: str = "7d",
        source: str = "xau_usd",
    ) -> dict:
        """
        Đưa ra prediction mới nhất.

        Returns:
            dict với predicted_price, trend, probabilities, confidence
        """
        if horizon not in self.trained_models:
            raise ValueError(f"Models chưa train cho horizon {horizon}")

        models = self.trained_models[horizon]

        # Build features cho data mới nhất
        df = self.feature_builder.build_features(source=source, include_macro=True)
        X, _, _, _ = self.feature_builder.get_train_data(df, horizon=horizon)

        if X.empty:
            return {}

        # Lấy row cuối (dữ liệu mới nhất)
        X_latest = X.iloc[[-1]]
        latest_date = df["date"].iloc[-1] if "date" in df.columns else "N/A"

        # Price prediction
        xgb_price = models["xgb_price"]
        price_pred, price_lower, price_upper = xgb_price.predict_with_confidence(X_latest)

        # Trend prediction
        xgb_trend = models["xgb_trend"]
        trend_pred = xgb_trend.predict(X_latest)[0]
        trend_proba = xgb_trend.predict_proba(X_latest)[0]

        result = {
            "date": str(latest_date),
            "horizon": horizon,
            "predicted_price": round(float(price_pred[0]), 2),
            "confidence_lower": round(float(price_lower[0]), 2),
            "confidence_upper": round(float(price_upper[0]), 2),
            "predicted_trend": int(trend_pred),
            "trend_probabilities": {
                "giam": round(float(trend_proba[0]), 4),
                "sideway": round(float(trend_proba[1]), 4),
                "tang": round(float(trend_proba[2]), 4),
            },
        }

        self.logger.info(
            f"Prediction ({horizon}): "
            f"Price=${result['predicted_price']:,.2f} "
            f"[${result['confidence_lower']:,.2f} - ${result['confidence_upper']:,.2f}], "
            f"Trend={['Giam','Sideway','Tang'][trend_pred]} "
            f"(p={trend_proba[trend_pred]:.2%})"
        )

        return result


# Convenience function
def train_models(horizon: str = "7d") -> dict:
    """Entry point train models."""
    trainer = ModelTrainer()
    return trainer.train_all(horizon=horizon)


if __name__ == "__main__":
    train_models("7d")
