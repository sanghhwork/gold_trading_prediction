"""
Gold Predictor - XGBoost Models
XGBoost cho price regression và trend classification.

XGBoost ưu điểm:
- Nhanh, hiệu quả với tabular data
- Xử lý tốt missing values
- Feature importance rõ ràng
- Ít cần feature scaling

Điểm mở rộng tương lai:
- Thêm Optuna hyperparameter tuning
- Thêm early stopping tự động
- Thêm SHAP explanations
"""

from typing import Optional

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.model_selection import TimeSeriesSplit

from app.services.models.base_model import BaseModel
from app.utils.constants import XGBOOST_N_ESTIMATORS, XGBOOST_MAX_DEPTH, XGBOOST_LEARNING_RATE
from app.utils.logger import get_logger

logger = get_logger(__name__)


class XGBoostPriceModel(BaseModel):
    """XGBoost cho dự đoán giá vàng (regression)."""

    def __init__(self, horizon: str = "7d"):
        super().__init__(f"xgboost_price_{horizon}", model_type="regression")
        self.horizon = horizon

    def train(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: Optional[pd.DataFrame] = None,
        y_val: Optional[pd.Series] = None,
        **kwargs,
    ):
        """Train XGBoost regressor."""
        self.feature_names = list(X_train.columns)
        self.logger.info(
            f"Training XGBoost price model ({self.horizon}): "
            f"X={X_train.shape}, features={len(self.feature_names)}"
        )

        params = {
            "n_estimators": kwargs.get("n_estimators", XGBOOST_N_ESTIMATORS),
            "max_depth": kwargs.get("max_depth", XGBOOST_MAX_DEPTH),
            "learning_rate": kwargs.get("learning_rate", XGBOOST_LEARNING_RATE),
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "reg_alpha": 0.1,
            "reg_lambda": 1.0,
            "random_state": 42,
            "n_jobs": -1,
        }

        self.model = xgb.XGBRegressor(**params)

        eval_set = []
        if X_val is not None and y_val is not None:
            eval_set = [(X_val, y_val)]

        self.model.fit(
            X_train, y_train,
            eval_set=eval_set if eval_set else None,
            verbose=False,
        )

        self.is_trained = True

        # Train metrics
        y_pred_train = self.model.predict(X_train)
        self.train_metrics = self._eval_regression(y_train.values, y_pred_train)
        self.logger.info(f"Train R2: {self.train_metrics['r2']:.4f}")

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Predict giá vàng."""
        if not self.is_trained:
            raise ValueError("Model chưa được train!")
        return self.model.predict(X)

    def predict_with_confidence(
        self, X: pd.DataFrame, n_estimators_range: int = 50
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Predict với confidence interval (dựa trên quantile regression).
        Returns: (predictions, lower_bound, upper_bound)
        """
        predictions = self.predict(X)

        # Ước lượng CI từ train RMSE
        rmse = self.train_metrics.get("rmse", 0)
        lower = predictions - 1.96 * rmse
        upper = predictions + 1.96 * rmse

        return predictions, lower, upper

    def get_feature_importance(self) -> Optional[pd.DataFrame]:
        """Feature importance từ XGBoost."""
        if not self.is_trained:
            return None

        importance = self.model.feature_importances_
        fi = pd.DataFrame({
            "feature": self.feature_names,
            "importance": importance,
        }).sort_values("importance", ascending=False)

        return fi


class XGBoostTrendModel(BaseModel):
    """XGBoost cho dự đoán xu hướng (classification: Tăng/Giảm/Sideway)."""

    def __init__(self, horizon: str = "7d"):
        super().__init__(f"xgboost_trend_{horizon}", model_type="classification")
        self.horizon = horizon

    def train(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: Optional[pd.DataFrame] = None,
        y_val: Optional[pd.Series] = None,
        **kwargs,
    ):
        """Train XGBoost classifier."""
        self.feature_names = list(X_train.columns)
        self.logger.info(
            f"Training XGBoost trend model ({self.horizon}): "
            f"X={X_train.shape}, classes={sorted(y_train.unique())}"
        )

        params = {
            "n_estimators": kwargs.get("n_estimators", XGBOOST_N_ESTIMATORS),
            "max_depth": kwargs.get("max_depth", XGBOOST_MAX_DEPTH),
            "learning_rate": kwargs.get("learning_rate", XGBOOST_LEARNING_RATE),
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "reg_alpha": 0.1,
            "reg_lambda": 1.0,
            "objective": "multi:softprob",
            "num_class": 3,
            "random_state": 42,
            "n_jobs": -1,
        }

        self.model = xgb.XGBClassifier(**params)

        eval_set = []
        if X_val is not None and y_val is not None:
            eval_set = [(X_val, y_val)]

        self.model.fit(
            X_train, y_train,
            eval_set=eval_set if eval_set else None,
            verbose=False,
        )

        self.is_trained = True

        # Train metrics
        y_pred_train = self.model.predict(X_train)
        self.train_metrics = self._eval_classification(y_train.values, y_pred_train)

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Predict xu hướng (0=Giảm, 1=Sideway, 2=Tăng)."""
        if not self.is_trained:
            raise ValueError("Model chưa được train!")
        return self.model.predict(X)

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Predict xác suất cho mỗi class. Shape: (n_samples, 3)."""
        if not self.is_trained:
            raise ValueError("Model chưa được train!")
        return self.model.predict_proba(X)

    def get_feature_importance(self) -> Optional[pd.DataFrame]:
        """Feature importance từ XGBoost."""
        if not self.is_trained:
            return None

        importance = self.model.feature_importances_
        return pd.DataFrame({
            "feature": self.feature_names,
            "importance": importance,
        }).sort_values("importance", ascending=False)
