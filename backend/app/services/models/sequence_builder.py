"""
Gold Predictor - Sequence Builder
Tạo sliding window sequences cho LSTM/GRU models.

Chuyển tabular features (N_samples, N_features) → sequences (N_samples, seq_len, N_features)
cho time-series deep learning.

Điểm mở rộng tương lai:
- Thêm multi-step target sequences
- Thêm attention mask cho missing data
"""

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler

from app.utils.constants import LSTM_SEQUENCE_LENGTH
from app.utils.logger import get_logger

logger = get_logger(__name__)


class SequenceBuilder:
    """
    Build sliding window sequences cho LSTM input.
    
    Input:  DataFrame (N_rows, N_features)
    Output: np.array (N_sequences, sequence_length, N_features), np.array (N_sequences,)
    """

    def __init__(self, sequence_length: int = LSTM_SEQUENCE_LENGTH):
        self.sequence_length = sequence_length
        self.feature_scaler = MinMaxScaler()
        self.target_scaler = MinMaxScaler()
        self.is_fitted = False
        self.logger = get_logger("sequence_builder")

    def fit_transform(
        self,
        X: pd.DataFrame,
        y: pd.Series,
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Fit scalers + tạo sequences từ training data.
        
        Returns: (X_sequences, y_targets) where
            X_sequences: shape (N, seq_len, n_features)
            y_targets: shape (N,)
        """
        # Scale features to [0, 1]
        X_scaled = self.feature_scaler.fit_transform(X.values)
        y_scaled = self.target_scaler.fit_transform(y.values.reshape(-1, 1)).flatten()
        self.is_fitted = True

        return self._create_sequences(X_scaled, y_scaled)

    def transform(
        self,
        X: pd.DataFrame,
        y: pd.Series = None,
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Transform test data (dùng fitted scalers) + tạo sequences.
        """
        if not self.is_fitted:
            raise ValueError("SequenceBuilder chưa được fit!")

        X_scaled = self.feature_scaler.transform(X.values)

        if y is not None:
            y_scaled = self.target_scaler.transform(y.values.reshape(-1, 1)).flatten()
            return self._create_sequences(X_scaled, y_scaled)
        else:
            # Predict mode: chỉ cần last sequence
            return self._create_sequences_no_target(X_scaled)

    def _create_sequences(
        self, X: np.ndarray, y: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray]:
        """Tạo sliding window sequences + target pairs."""
        sequences = []
        targets = []

        for i in range(self.sequence_length, len(X)):
            sequences.append(X[i - self.sequence_length:i])
            targets.append(y[i])

        X_seq = np.array(sequences)
        y_seq = np.array(targets)

        self.logger.info(
            f"Created sequences: X={X_seq.shape}, y={y_seq.shape}"
        )
        return X_seq, y_seq

    def _create_sequences_no_target(self, X: np.ndarray) -> tuple[np.ndarray, None]:
        """Tạo sequences cho prediction (không có target)."""
        if len(X) < self.sequence_length:
            self.logger.warning(
                f"Data ({len(X)} rows) < sequence_length ({self.sequence_length}). "
                f"Padding with zeros."
            )
            padding = np.zeros((self.sequence_length - len(X), X.shape[1]))
            X = np.vstack([padding, X])

        # Lấy last sequence
        last_seq = X[-self.sequence_length:].reshape(1, self.sequence_length, X.shape[1])
        return last_seq, None

    def inverse_transform_target(self, y_scaled: np.ndarray) -> np.ndarray:
        """Convert scaled predictions back to original scale."""
        if not self.is_fitted:
            raise ValueError("SequenceBuilder chưa được fit!")
        return self.target_scaler.inverse_transform(
            y_scaled.reshape(-1, 1)
        ).flatten()

    def save_scalers(self, filepath: str):
        """Save scalers cho production inference."""
        import joblib
        joblib.dump({
            "feature_scaler": self.feature_scaler,
            "target_scaler": self.target_scaler,
            "sequence_length": self.sequence_length,
        }, filepath)
        self.logger.info(f"Scalers saved: {filepath}")

    def load_scalers(self, filepath: str):
        """Load scalers."""
        import joblib
        data = joblib.load(filepath)
        self.feature_scaler = data["feature_scaler"]
        self.target_scaler = data["target_scaler"]
        self.sequence_length = data["sequence_length"]
        self.is_fitted = True
        self.logger.info(f"Scalers loaded: {filepath}")
