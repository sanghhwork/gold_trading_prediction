"""
Gold Predictor - Base Model
Abstract base class cho tất cả ML models.

Điểm mở rộng tương lai:
- Thêm model registry (MLflow)
- Thêm hyperparameter tuning (Optuna)
- Thêm model versioning
"""

from abc import ABC, abstractmethod
from pathlib import Path
from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd
import joblib

from app.utils.logger import get_logger

logger = get_logger(__name__)

# Thư mục lưu models
MODELS_DIR = Path(__file__).parent.parent.parent.parent / "saved_models"
MODELS_DIR.mkdir(exist_ok=True)


class BaseModel(ABC):
    """Abstract base class cho ML models."""

    def __init__(self, name: str, model_type: str):
        """
        Args:
            name: Tên model (e.g. "xgboost_price_7d")
            model_type: "regression" hoặc "classification"
        """
        self.name = name
        self.model_type = model_type
        self.model = None
        self.is_trained = False
        self.train_metrics = {}
        self.feature_names = []
        self.logger = get_logger(f"model.{name}")

    @abstractmethod
    def train(self, X_train: pd.DataFrame, y_train: pd.Series, **kwargs):
        """Train model."""
        pass

    @abstractmethod
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Predict."""
        pass

    def evaluate(
        self,
        X_test: pd.DataFrame,
        y_test: pd.Series,
    ) -> dict:
        """Evaluate model trên test set."""
        if not self.is_trained:
            raise ValueError("Model chưa được train!")

        y_pred = self.predict(X_test)

        if self.model_type == "regression":
            return self._eval_regression(y_test.values, y_pred)
        else:
            return self._eval_classification(y_test.values, y_pred)

    def _eval_regression(self, y_true: np.ndarray, y_pred: np.ndarray) -> dict:
        """Metrics cho regression."""
        from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

        mae = mean_absolute_error(y_true, y_pred)
        rmse = np.sqrt(mean_squared_error(y_true, y_pred))
        r2 = r2_score(y_true, y_pred)

        # MAPE (Mean Absolute Percentage Error)
        nonzero = y_true != 0
        mape = np.mean(np.abs((y_true[nonzero] - y_pred[nonzero]) / y_true[nonzero])) * 100

        metrics = {
            "mae": round(mae, 2),
            "rmse": round(rmse, 2),
            "r2": round(r2, 4),
            "mape": round(mape, 2),
        }

        self.logger.info(
            f"[{self.name}] Regression metrics: "
            f"MAE={mae:.2f}, RMSE={rmse:.2f}, R2={r2:.4f}, MAPE={mape:.2f}%"
        )
        return metrics

    def _eval_classification(self, y_true: np.ndarray, y_pred: np.ndarray) -> dict:
        """Metrics cho classification."""
        from sklearn.metrics import accuracy_score, f1_score, classification_report

        accuracy = accuracy_score(y_true, y_pred)
        f1 = f1_score(y_true, y_pred, average="weighted")

        metrics = {
            "accuracy": round(accuracy, 4),
            "f1_weighted": round(f1, 4),
        }

        self.logger.info(
            f"[{self.name}] Classification metrics: "
            f"Accuracy={accuracy:.4f}, F1={f1:.4f}"
        )

        # Detailed report
        report = classification_report(y_true, y_pred, output_dict=True)
        metrics["classification_report"] = report

        return metrics

    def save(self, suffix: str = "") -> str:
        """Lưu model ra file."""
        if not self.is_trained:
            raise ValueError("Model chưa được train!")

        filename = f"{self.name}{suffix}.joblib"
        filepath = MODELS_DIR / filename

        save_data = {
            "model": self.model,
            "name": self.name,
            "model_type": self.model_type,
            "feature_names": self.feature_names,
            "train_metrics": self.train_metrics,
            "saved_at": datetime.now().isoformat(),
        }

        joblib.dump(save_data, filepath)
        self.logger.info(f"Model saved: {filepath}")
        return str(filepath)

    def load(self, filepath: str):
        """Load model từ file."""
        data = joblib.load(filepath)
        self.model = data["model"]
        self.name = data["name"]
        self.model_type = data["model_type"]
        self.feature_names = data["feature_names"]
        self.train_metrics = data["train_metrics"]
        self.is_trained = True
        self.logger.info(f"Model loaded: {filepath}")

    def get_feature_importance(self) -> Optional[pd.DataFrame]:
        """Lấy feature importance (nếu model hỗ trợ)."""
        return None
