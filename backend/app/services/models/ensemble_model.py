"""
Gold Predictor - Ensemble Model
Kết hợp nhiều models để đưa ra dự đoán tốt hơn.

Strategy:
- Price: Weighted average of individual model predictions
- Trend: Voting (majority) hoặc average probabilities

Điểm mở rộng tương lai:
- Thêm stacking ensemble (meta-learner)
- Thêm dynamic weights (dựa trên recent performance)
- Thêm model selection tự động
"""

from typing import Optional

import numpy as np
import pandas as pd

from app.services.models.base_model import BaseModel
from app.utils.constants import TREND_LABELS
from app.utils.logger import get_logger

logger = get_logger(__name__)


class EnsemblePriceModel(BaseModel):
    """Ensemble cho price prediction: weighted average."""

    def __init__(self, horizon: str = "7d"):
        super().__init__(f"ensemble_price_{horizon}", model_type="regression")
        self.horizon = horizon
        self.sub_models: list[BaseModel] = []
        self.weights: list[float] = []

    def add_model(self, model: BaseModel, weight: float = 1.0):
        """Thêm model vào ensemble."""
        self.sub_models.append(model)
        self.weights.append(weight)
        self.logger.info(f"Thêm {model.name} vào ensemble (weight={weight})")

    def train(self, X_train: pd.DataFrame, y_train: pd.Series, **kwargs):
        """Ensemble không cần train riêng - các sub-models đã train."""
        self.feature_names = list(X_train.columns)
        self.is_trained = all(m.is_trained for m in self.sub_models)

        if not self.is_trained:
            untrained = [m.name for m in self.sub_models if not m.is_trained]
            raise ValueError(f"Models chưa train: {untrained}")

        self.logger.info(
            f"Ensemble price ready: {len(self.sub_models)} models, "
            f"weights={self.weights}"
        )

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Weighted average prediction."""
        if not self.sub_models:
            raise ValueError("Chưa có sub-models!")

        predictions = []
        for model in self.sub_models:
            pred = model.predict(X)
            predictions.append(pred)

        predictions = np.array(predictions)
        weights = np.array(self.weights) / sum(self.weights)

        return np.average(predictions, axis=0, weights=weights)

    def predict_with_confidence(self, X: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Predict + confidence interval từ model disagreement."""
        predictions = []
        for model in self.sub_models:
            predictions.append(model.predict(X))

        predictions = np.array(predictions)
        weights = np.array(self.weights) / sum(self.weights)

        mean_pred = np.average(predictions, axis=0, weights=weights)
        std_pred = np.sqrt(np.average((predictions - mean_pred) ** 2, axis=0, weights=weights))

        lower = mean_pred - 1.96 * std_pred
        upper = mean_pred + 1.96 * std_pred

        return mean_pred, lower, upper


class EnsembleTrendModel(BaseModel):
    """Ensemble cho trend classification: probability averaging."""

    def __init__(self, horizon: str = "7d"):
        super().__init__(f"ensemble_trend_{horizon}", model_type="classification")
        self.horizon = horizon
        self.sub_models: list[BaseModel] = []
        self.weights: list[float] = []

    def add_model(self, model: BaseModel, weight: float = 1.0):
        """Thêm model vào ensemble."""
        self.sub_models.append(model)
        self.weights.append(weight)

    def train(self, X_train: pd.DataFrame, y_train: pd.Series, **kwargs):
        """Ensemble không cần train riêng."""
        self.feature_names = list(X_train.columns)
        self.is_trained = all(m.is_trained for m in self.sub_models)

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Majority voting."""
        all_preds = []
        for model in self.sub_models:
            all_preds.append(model.predict(X))

        all_preds = np.array(all_preds)  # (n_models, n_samples)

        # Majority vote cho từng sample
        from scipy import stats
        result, _ = stats.mode(all_preds, axis=0, keepdims=False)
        return result.astype(int)

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Average probability across models."""
        all_probas = []
        for model in self.sub_models:
            if hasattr(model, "predict_proba"):
                all_probas.append(model.predict_proba(X))

        if not all_probas:
            # Fallback: one-hot from predictions
            preds = self.predict(X)
            probas = np.zeros((len(preds), 3))
            for i, p in enumerate(preds):
                probas[i, p] = 1.0
            return probas

        weights = np.array(self.weights[:len(all_probas)]) / sum(self.weights[:len(all_probas)])

        avg_proba = np.average(np.array(all_probas), axis=0, weights=weights)
        return avg_proba
