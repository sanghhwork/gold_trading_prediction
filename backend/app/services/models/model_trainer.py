"""
Gold Predictor - Model Trainer V2.0
Orchestrate toàn bộ quá trình train, evaluate và save models.

V2 Changes:
- Return-based prediction thay vì price prediction (fix extrapolation)
- Walk-forward validation (expanding window)
- Purge & Embargo (chống data leakage)
- Support multiple model types (XGBoost, LightGBM, LSTM)

Pipeline: Build Features → Split Data → Train Models → Evaluate → Ensemble → Save

Điểm mở rộng tương lai:
- Thêm auto hyperparameter tuning (Optuna)
- Thêm model comparison dashboard
- Thêm dynamic ensemble weights
"""

from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.model_selection import TimeSeriesSplit

from app.services.feature_engine.feature_builder import FeatureBuilder
from app.services.models.xgboost_models import XGBoostPriceModel, XGBoostTrendModel
from app.services.models.lightgbm_models import LGBMReturnModel, LGBMTrendModel
from app.services.models.ensemble_model import EnsemblePriceModel, EnsembleTrendModel
from app.utils.constants import (
    PREDICTION_HORIZONS,
    TRAIN_WINDOW_DAYS,
    TEST_WINDOW_DAYS,
    WALK_FORWARD_STEP,
    EMBARGO_DAYS,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ModelTrainer:
    """
    Orchestrate model training pipeline V2.0.

    Key improvements:
    - predict return (%) instead of absolute price → fixes XGBoost extrapolation issue
    - walk-forward validation → reliable out-of-sample metrics
    - purge & embargo → eliminates data leakage

    Usage:
        trainer = ModelTrainer()
        results = trainer.train_all(horizon="7d")
        prediction = trainer.predict("7d")
    """

    def __init__(self):
        self.logger = get_logger("model_trainer")
        self.feature_builder = FeatureBuilder()
        self.trained_models = {}
        self._cached_features = None  # Cache feature matrix

    def _build_features_cached(self, source: str = "xau_usd") -> pd.DataFrame:
        """Build features với caching (tránh rebuild khi train nhiều horizons)."""
        if self._cached_features is not None:
            return self._cached_features
        
        df = self.feature_builder.build_features(source=source, include_macro=True)
        self._cached_features = df
        return df

    def train_all(
        self,
        horizon: str = "7d",
        test_size: float = 0.2,
        source: str = "xau_usd",
    ) -> dict:
        """
        Train tất cả models cho 1 horizon (production training: full data).
        
        V2: Predict return (%) thay vì price tuyệt đối.
        """
        self.logger.info(f"{'='*60}")
        self.logger.info(f"TRAINING PIPELINE V2 - Horizon: {horizon}")
        self.logger.info(f"{'='*60}")

        # 1. Build features
        self.logger.info("Step 1: Building features...")
        df = self._build_features_cached(source=source)
        if df.empty:
            self.logger.error("Feature matrix rỗng!")
            return {}

        # 2. Get train data — RETURN target thay vì price target
        X, y_price, y_trend, y_return = self.feature_builder.get_train_data(df, horizon=horizon)
        self.logger.info(f"Data shape: X={X.shape}")

        # 3. Time-series split (IMPORTANT: không shuffle!)
        # Apply purge & embargo
        purge_size = PREDICTION_HORIZONS[horizon]
        split_idx = int(len(X) * (1 - test_size))
        
        # Purge: bỏ rows cuối train (vì target nhìn tới future)
        # Embargo: thêm gap giữa train/test
        train_end = split_idx - purge_size - EMBARGO_DAYS
        test_start = split_idx
        
        X_train, X_test = X.iloc[:train_end], X.iloc[test_start:]
        y_return_train, y_return_test = y_return.iloc[:train_end], y_return.iloc[test_start:]
        y_trend_train, y_trend_test = y_trend.iloc[:train_end], y_trend.iloc[test_start:]

        self.logger.info(
            f"Train: {len(X_train)} samples, Test: {len(X_test)} samples, "
            f"Purge: {purge_size}d, Embargo: {EMBARGO_DAYS}d, "
            f"Effective gap: {test_start - train_end}d"
        )

        results = {}

        # 4. Train XGBoost Return Model (V2: predict return %)
        self.logger.info("\nStep 4a: Training XGBoost Return (V2)...")
        xgb_return = XGBoostPriceModel(horizon=horizon)
        xgb_return.train(X_train, y_return_train, X_val=X_test, y_val=y_return_test)
        return_metrics = xgb_return.evaluate(X_test, y_return_test)
        results["xgboost_return"] = return_metrics

        # 5. Train XGBoost Trend Model
        self.logger.info("\nStep 4b: Training XGBoost Trend...")
        xgb_trend = XGBoostTrendModel(horizon=horizon)
        xgb_trend.train(X_train, y_trend_train, X_val=X_test, y_val=y_trend_test)
        trend_metrics = xgb_trend.evaluate(X_test, y_trend_test)
        results["xgboost_trend"] = trend_metrics

        # 6. Train LightGBM Models
        self.logger.info("\nStep 5a: Training LightGBM Return...")
        lgbm_return = LGBMReturnModel(horizon=horizon)
        lgbm_return.train(X_train, y_return_train, X_val=X_test, y_val=y_return_test)
        lgbm_ret_metrics = lgbm_return.evaluate(X_test, y_return_test)
        results["lgbm_return"] = lgbm_ret_metrics

        self.logger.info("\nStep 5b: Training LightGBM Trend...")
        lgbm_trend = LGBMTrendModel(horizon=horizon)
        lgbm_trend.train(X_train, y_trend_train, X_val=X_test, y_val=y_trend_test)
        lgbm_trend_metrics = lgbm_trend.evaluate(X_test, y_trend_test)
        results["lgbm_trend"] = lgbm_trend_metrics

        # 7. Train LSTM Models (optional — TF may not be available)
        lstm_return = None
        lstm_trend = None
        try:
            from app.services.models.lstm_models import LSTMReturnModel, LSTMTrendModel

            self.logger.info("\nStep 6a: Training LSTM Return...")
            lstm_return = LSTMReturnModel(horizon=horizon)
            lstm_return.train(X_train, y_return_train, X_val=X_test, y_val=y_return_test)
            lstm_ret_metrics = lstm_return.evaluate(X_test, y_return_test)
            results["lstm_return"] = lstm_ret_metrics

            self.logger.info("\nStep 6b: Training LSTM Trend...")
            lstm_trend = LSTMTrendModel(horizon=horizon)
            lstm_trend.train(X_train, y_trend_train, X_val=X_test, y_val=y_trend_test)
            lstm_trend_metrics = lstm_trend.evaluate(X_test, y_trend_test)
            results["lstm_trend"] = lstm_trend_metrics
        except Exception as e:
            self.logger.warning(f"LSTM training skipped: {e}")

        # 8. True Ensemble (V2: 2-3 models)
        self.logger.info("\nStep 7: Building True Ensemble...")
        ensemble_return = EnsemblePriceModel(horizon=horizon)
        ensemble_return.add_model(xgb_return, weight=0.4)
        ensemble_return.add_model(lgbm_return, weight=0.3)
        if lstm_return and lstm_return.is_trained:
            ensemble_return.add_model(lstm_return, weight=0.3)
        ensemble_return.train(X_train, y_return_train)

        ensemble_trend = EnsembleTrendModel(horizon=horizon)
        ensemble_trend.add_model(xgb_trend, weight=0.4)
        ensemble_trend.add_model(lgbm_trend, weight=0.3)
        if lstm_trend and lstm_trend.is_trained:
            ensemble_trend.add_model(lstm_trend, weight=0.3)
        ensemble_trend.train(X_train, y_trend_train)

        # 9. Save all models
        self.logger.info("\nStep 8: Saving models...")
        xgb_return.save()
        xgb_trend.save()
        lgbm_return.save()
        lgbm_trend.save()
        if lstm_return and lstm_return.is_trained:
            lstm_return.save()
        if lstm_trend and lstm_trend.is_trained:
            lstm_trend.save()
        ensemble_return.save()
        ensemble_trend.save()

        self.trained_models[horizon] = {
            "xgb_price": xgb_return,
            "xgb_trend": xgb_trend,
            "lgbm_price": lgbm_return,
            "lgbm_trend": lgbm_trend,
            "lstm_price": lstm_return,
            "lstm_trend": lstm_trend,
            "ensemble_price": ensemble_return,
            "ensemble_trend": ensemble_trend,
        }

        # Feature importance (from best tree model)
        fi = xgb_return.get_feature_importance()
        if fi is not None:
            self.logger.info("\nTop 10 features (XGBoost return):")
            for _, row in fi.head(10).iterrows():
                self.logger.info(f"  {row['feature']}: {row['importance']:.4f}")

        # Summary
        self.logger.info(f"\n{'='*60}")
        self.logger.info("TRAINING SUMMARY V2 (True Ensemble):")
        self.logger.info(f"  XGBoost Return  - MAE: {return_metrics['mae']:.4f}%, R2: {return_metrics['r2']:.4f}")
        self.logger.info(f"  LightGBM Return - MAE: {lgbm_ret_metrics['mae']:.4f}%, R2: {lgbm_ret_metrics['r2']:.4f}")
        if 'lstm_return' in results:
            self.logger.info(f"  LSTM Return     - MAE: {results['lstm_return']['mae']:.4f}%, R2: {results['lstm_return']['r2']:.4f}")
        self.logger.info(f"  XGBoost Trend   - Accuracy: {trend_metrics['accuracy']:.4f}")
        self.logger.info(f"  LightGBM Trend  - Accuracy: {lgbm_trend_metrics['accuracy']:.4f}")
        if 'lstm_trend' in results:
            self.logger.info(f"  LSTM Trend      - Accuracy: {results['lstm_trend']['accuracy']:.4f}")
        self.logger.info(f"  Ensemble: {len(ensemble_return.sub_models)} return + {len(ensemble_trend.sub_models)} trend models")
        self.logger.info(f"{'='*60}")

        return results

    def walk_forward_validate(
        self,
        horizon: str = "7d",
        source: str = "xau_usd",
        min_train_size: int = TRAIN_WINDOW_DAYS,
        test_size: int = TEST_WINDOW_DAYS,
        step_size: int = WALK_FORWARD_STEP,
    ) -> dict:
        """
        Walk-forward validation (expanding window).
        
        Đây là cách ĐÚNG để đo model performance cho financial time series.
        
        Flow:
            Window 1: Train [====756d====]  Test [==252d==]
            Window 2: Train [=====777d=====]  Test [==252d==]  (step +21d)
            ...
        
        Returns:
            dict: {
                "windows": [{ metrics per window }],
                "avg_return_metrics": { avg MAE, RMSE, R² },
                "avg_trend_metrics": { avg accuracy, F1 },
                "std_return_metrics": { std of metrics },
                "n_windows": int,
            }
        """
        self.logger.info(f"\n{'#'*60}")
        self.logger.info(f"WALK-FORWARD VALIDATION - Horizon: {horizon}")
        self.logger.info(f"  min_train={min_train_size}, test={test_size}, step={step_size}")
        self.logger.info(f"{'#'*60}")

        # 1. Build features
        df = self._build_features_cached(source=source)
        if df.empty:
            self.logger.error("Feature matrix rỗng!")
            return {}

        X, y_price, y_trend, y_return = self.feature_builder.get_train_data(df, horizon=horizon)
        total_samples = len(X)
        purge_size = PREDICTION_HORIZONS[horizon]

        self.logger.info(f"Total samples: {total_samples}")

        # 2. Walk-forward loop
        windows = []
        window_start = 0

        while True:
            train_end_raw = window_start + min_train_size + (len(windows) * step_size)
            train_end = train_end_raw - purge_size - EMBARGO_DAYS
            test_start = train_end_raw
            test_end = test_start + test_size

            if test_end > total_samples:
                break

            X_train = X.iloc[window_start:train_end]
            X_test = X.iloc[test_start:test_end]
            y_ret_train = y_return.iloc[window_start:train_end]
            y_ret_test = y_return.iloc[test_start:test_end]
            y_trend_train = y_trend.iloc[window_start:train_end]
            y_trend_test = y_trend.iloc[test_start:test_end]

            if len(X_train) < 100 or len(X_test) < 10:
                break

            # Train models
            xgb_ret = XGBoostPriceModel(horizon=horizon)
            xgb_ret.train(X_train, y_ret_train)
            ret_metrics = xgb_ret.evaluate(X_test, y_ret_test)

            xgb_trend_model = XGBoostTrendModel(horizon=horizon)
            xgb_trend_model.train(X_train, y_trend_train)
            trend_metrics = xgb_trend_model.evaluate(X_test, y_trend_test)

            window_result = {
                "window": len(windows) + 1,
                "train_size": len(X_train),
                "test_size": len(X_test),
                "return_mae": ret_metrics["mae"],
                "return_rmse": ret_metrics["rmse"],
                "return_r2": ret_metrics["r2"],
                "trend_accuracy": trend_metrics["accuracy"],
                "trend_f1": trend_metrics["f1_weighted"],
            }
            windows.append(window_result)

            self.logger.info(
                f"  Window {window_result['window']}: "
                f"train={len(X_train)}, test={len(X_test)}, "
                f"MAE={ret_metrics['mae']:.4f}%, "
                f"Acc={trend_metrics['accuracy']:.2%}"
            )

        if not windows:
            self.logger.error("Không đủ data cho walk-forward validation!")
            return {}

        # 3. Aggregate metrics
        result = {
            "windows": windows,
            "n_windows": len(windows),
            "avg_return_metrics": {
                "mae": float(np.mean([w["return_mae"] for w in windows])),
                "rmse": float(np.mean([w["return_rmse"] for w in windows])),
                "r2": float(np.mean([w["return_r2"] for w in windows])),
            },
            "avg_trend_metrics": {
                "accuracy": float(np.mean([w["trend_accuracy"] for w in windows])),
                "f1": float(np.mean([w["trend_f1"] for w in windows])),
            },
            "std_return_metrics": {
                "mae": float(np.std([w["return_mae"] for w in windows])),
                "rmse": float(np.std([w["return_rmse"] for w in windows])),
                "r2": float(np.std([w["return_r2"] for w in windows])),
            },
        }

        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"WALK-FORWARD RESULTS ({len(windows)} windows):")
        self.logger.info(
            f"  Return MAE: {result['avg_return_metrics']['mae']:.4f}% "
            f"± {result['std_return_metrics']['mae']:.4f}%"
        )
        self.logger.info(
            f"  Trend Accuracy: {result['avg_trend_metrics']['accuracy']:.2%} "
            f"± {float(np.std([w['trend_accuracy'] for w in windows])):.2%}"
        )
        self.logger.info(f"{'='*60}")

        return result

    def train_all_horizons(self, source: str = "xau_usd") -> dict:
        """Train tất cả models cho tất cả horizons (1d, 7d, 30d)."""
        self._cached_features = None  # Clear cache
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
        
        V2: Predict return (%) → convert ngược lại giá tuyệt đối.
        
        Returns:
            dict với predicted_price, trend, probabilities, confidence
        """
        if horizon not in self.trained_models:
            raise ValueError(f"Models chưa train cho horizon {horizon}")

        models = self.trained_models[horizon]

        # Build features cho data mới nhất
        df = self._build_features_cached(source=source)
        X, _, _, _ = self.feature_builder.get_train_data(df, horizon=horizon)

        if X.empty:
            return {}

        # Lấy row cuối (dữ liệu mới nhất)
        X_latest = X.iloc[[-1]]
        latest_date = df["date"].iloc[-1] if "date" in df.columns else "N/A"
        
        # Current price (để convert return → price)
        current_price = float(df["close"].iloc[-1])

        # Return prediction (V2: predict %)
        xgb_price = models["xgb_price"]
        return_pred, return_lower, return_upper = xgb_price.predict_with_confidence(X_latest)
        predicted_return = float(return_pred[0])
        
        # Convert return → absolute price
        predicted_price = current_price * (1 + predicted_return / 100)
        price_lower = current_price * (1 + float(return_lower[0]) / 100)
        price_upper = current_price * (1 + float(return_upper[0]) / 100)

        # Trend prediction
        xgb_trend = models["xgb_trend"]
        trend_pred = xgb_trend.predict(X_latest)[0]
        trend_proba = xgb_trend.predict_proba(X_latest)[0]

        result = {
            "date": str(latest_date),
            "horizon": horizon,
            "current_price": round(current_price, 2),
            "predicted_return_pct": round(predicted_return, 4),
            "predicted_price": round(predicted_price, 2),
            "confidence_lower": round(price_lower, 2),
            "confidence_upper": round(price_upper, 2),
            "predicted_trend": int(trend_pred),
            "trend_probabilities": {
                "giam": round(float(trend_proba[0]), 4),
                "sideway": round(float(trend_proba[1]), 4),
                "tang": round(float(trend_proba[2]), 4),
            },
        }

        self.logger.info(
            f"Prediction V2 ({horizon}): "
            f"Return={predicted_return:+.2f}%, "
            f"Price=${result['predicted_price']:,.2f} "
            f"[${result['confidence_lower']:,.2f} - ${result['confidence_upper']:,.2f}], "
            f"Trend={['Giảm','Sideway','Tăng'][trend_pred]} "
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
