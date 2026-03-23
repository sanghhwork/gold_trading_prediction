"""
Gold Predictor - LightGBM Models
LightGBM cho return prediction và trend classification.

LightGBM vs XGBoost:
- Nhanh hơn (histogram-based splitting)
- Ít memory hơn
- Tốt với large datasets
- Diversity cho ensemble (khác algorithm = khác prediction patterns)

Điểm mở rộng tương lai:
- Thêm CatBoost (3rd tree-based model)
- Thêm custom loss functions
"""

from typing import Optional

import numpy as np
import pandas as pd
import lightgbm as lgb

from app.services.models.base_model import BaseModel
from app.utils.logger import get_logger

logger = get_logger(__name__)


class LGBMReturnModel(BaseModel):
    """LightGBM cho return prediction (regression)."""

    def __init__(self, horizon: str = "7d"):
        super().__init__(f"lgbm_return_{horizon}", model_type="regression")
        self.horizon = horizon

    def train(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: Optional[pd.DataFrame] = None,
        y_val: Optional[pd.Series] = None,
        **kwargs,
    ):
        """Train LightGBM regressor."""
        self.feature_names = list(X_train.columns)
        self.logger.info(
            f"Training LightGBM return model ({self.horizon}): X={X_train.shape}"
        )

        params = {
            "n_estimators": kwargs.get("n_estimators", 500),
            "num_leaves": kwargs.get("num_leaves", 31),
            "max_depth": kwargs.get("max_depth", -1),
            "learning_rate": kwargs.get("learning_rate", 0.05),
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "min_child_samples": 20,
            "reg_alpha": 0.1,
            "reg_lambda": 1.0,
            "random_state": 42,
            "n_jobs": -1,
            "verbose": -1,
        }

        self.model = lgb.LGBMRegressor(**params)

        eval_set = []
        if X_val is not None and y_val is not None:
            eval_set = [(X_val, y_val)]

        self.model.fit(
            X_train, y_train,
            eval_set=eval_set if eval_set else None,
        )

        self.is_trained = True

        y_pred_train = self.model.predict(X_train)
        self.train_metrics = self._eval_regression(y_train.values, y_pred_train)
        self.logger.info(f"Train R2: {self.train_metrics['r2']:.4f}")

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Predict return %."""
        if not self.is_trained:
            raise ValueError("Model chưa được train!")
        return self.model.predict(X)

    def predict_with_confidence(
        self, X: pd.DataFrame, n_estimators_range: int = 50
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Predict với confidence interval."""
        predictions = self.predict(X)
        rmse = self.train_metrics.get("rmse", 0)
        lower = predictions - 1.96 * rmse
        upper = predictions + 1.96 * rmse
        return predictions, lower, upper

    def get_feature_importance(self) -> Optional[pd.DataFrame]:
        """Feature importance từ LightGBM."""
        if not self.is_trained:
            return None
        importance = self.model.feature_importances_
        return pd.DataFrame({
            "feature": self.feature_names,
            "importance": importance,
        }).sort_values("importance", ascending=False)


class LGBMTrendModel(BaseModel):
    """LightGBM cho trend classification."""

    def __init__(self, horizon: str = "7d"):
        super().__init__(f"lgbm_trend_{horizon}", model_type="classification")
        self.horizon = horizon

    def train(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: Optional[pd.DataFrame] = None,
        y_val: Optional[pd.Series] = None,
        **kwargs,
    ):
        """Train LightGBM classifier."""
        self.feature_names = list(X_train.columns)
        self.logger.info(
            f"Training LightGBM trend model ({self.horizon}): "
            f"X={X_train.shape}, classes={sorted(y_train.unique())}"
        )

        params = {
            "n_estimators": kwargs.get("n_estimators", 500),
            "num_leaves": kwargs.get("num_leaves", 31),
            "max_depth": kwargs.get("max_depth", -1),
            "learning_rate": kwargs.get("learning_rate", 0.05),
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "min_child_samples": 20,
            "objective": "multiclass",
            "num_class": 3,
            "random_state": 42,
            "n_jobs": -1,
            "verbose": -1,
        }

        self.model = lgb.LGBMClassifier(**params)

        eval_set = []
        if X_val is not None and y_val is not None:
            eval_set = [(X_val, y_val)]

        self.model.fit(
            X_train, y_train,
            eval_set=eval_set if eval_set else None,
        )

        self.is_trained = True

        y_pred_train = self.model.predict(X_train)
        self.train_metrics = self._eval_classification(y_train.values, y_pred_train)

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Predict trend (0=Giảm, 1=Sideway, 2=Tăng)."""
        if not self.is_trained:
            raise ValueError("Model chưa được train!")
        return self.model.predict(X)

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Predict probability cho mỗi class."""
        if not self.is_trained:
            raise ValueError("Model chưa được train!")
        return self.model.predict_proba(X)

    def get_feature_importance(self) -> Optional[pd.DataFrame]:
        """Feature importance."""
        if not self.is_trained:
            return None
        importance = self.model.feature_importances_
        return pd.DataFrame({
            "feature": self.feature_names,
            "importance": importance,
        }).sort_values("importance", ascending=False)
