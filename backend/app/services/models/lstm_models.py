"""
Gold Predictor - LSTM Models
Deep Learning models cho return prediction và trend classification.

LSTM xử lý sequence data, có khả năng:
- Capture temporal patterns (SMA crossovers, momentum shifts)
- Extrapolate ngoài training range (không bị giới hạn như XGBoost)

Architecture:
    Input: (batch, LSTM_SEQUENCE_LENGTH=60, n_features)
    → LSTM(64, return_sequences=True) → Dropout(0.2)
    → LSTM(32) → Dropout(0.2)
    → Dense(16, relu) → Dense(1)

Override save/load: Keras model dùng model.save() thay vì joblib.

Điểm mở rộng tương lai:
- Thêm GRU variant
- Thêm Bidirectional LSTM
- Thêm Attention layer
- Thêm Transformer encoder
"""

import os
from pathlib import Path
from typing import Optional
from datetime import datetime

import numpy as np
import pandas as pd

from app.services.models.base_model import BaseModel, MODELS_DIR
from app.services.models.sequence_builder import SequenceBuilder
from app.utils.constants import (
    LSTM_SEQUENCE_LENGTH, LSTM_EPOCHS, LSTM_BATCH_SIZE,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Suppress TensorFlow warnings
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"


class LSTMReturnModel(BaseModel):
    """LSTM cho dự đoán return % (regression)."""

    def __init__(self, horizon: str = "7d"):
        super().__init__(f"lstm_return_{horizon}", model_type="regression")
        self.horizon = horizon
        self.sequence_builder = SequenceBuilder(sequence_length=LSTM_SEQUENCE_LENGTH)

    def _build_model(self, n_features: int):
        """Build LSTM architecture."""
        from tensorflow.keras.models import Sequential
        from tensorflow.keras.layers import LSTM, Dense, Dropout
        from tensorflow.keras.optimizers import Adam

        model = Sequential([
            LSTM(64, return_sequences=True,
                 input_shape=(LSTM_SEQUENCE_LENGTH, n_features)),
            Dropout(0.2),
            LSTM(32, return_sequences=False),
            Dropout(0.2),
            Dense(16, activation="relu"),
            Dense(1),  # Predict return %
        ])

        model.compile(
            optimizer=Adam(learning_rate=0.001),
            loss="mse",
            metrics=["mae"],
        )

        self.logger.info(
            f"LSTM model built: input=({LSTM_SEQUENCE_LENGTH}, {n_features}), "
            f"params={model.count_params():,}"
        )
        return model

    def train(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: Optional[pd.DataFrame] = None,
        y_val: Optional[pd.Series] = None,
        **kwargs,
    ):
        """Train LSTM model."""
        from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau

        self.feature_names = list(X_train.columns)
        self.logger.info(
            f"Training LSTM return model ({self.horizon}): "
            f"X={X_train.shape}, seq_len={LSTM_SEQUENCE_LENGTH}"
        )

        # Build sequences
        X_seq, y_seq = self.sequence_builder.fit_transform(X_train, y_train)
        n_features = X_seq.shape[2]

        # Build model
        self.model = self._build_model(n_features)

        # Callbacks
        callbacks = [
            EarlyStopping(
                monitor="val_loss" if X_val is not None else "loss",
                patience=10,
                restore_best_weights=True,
            ),
            ReduceLROnPlateau(
                monitor="val_loss" if X_val is not None else "loss",
                factor=0.5,
                patience=5,
            ),
        ]

        # Validation data
        validation_data = None
        if X_val is not None and y_val is not None:
            X_val_seq, y_val_seq = self.sequence_builder.transform(X_val, y_val)
            if len(X_val_seq) > 0:
                validation_data = (X_val_seq, y_val_seq)

        # Train
        epochs = kwargs.get("epochs", LSTM_EPOCHS)
        batch_size = kwargs.get("batch_size", LSTM_BATCH_SIZE)

        history = self.model.fit(
            X_seq, y_seq,
            epochs=epochs,
            batch_size=batch_size,
            validation_data=validation_data,
            callbacks=callbacks,
            verbose=0,
        )

        self.is_trained = True

        # Log training results
        final_loss = history.history["loss"][-1]
        best_epoch = len(history.history["loss"])
        self.logger.info(f"LSTM trained: {best_epoch} epochs, final_loss={final_loss:.6f}")

        # Train metrics (on original scale)
        y_pred_scaled = self.model.predict(X_seq, verbose=0).flatten()
        y_pred = self.sequence_builder.inverse_transform_target(y_pred_scaled)
        y_true = self.sequence_builder.inverse_transform_target(y_seq)
        self.train_metrics = self._eval_regression(y_true, y_pred)

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Predict return % từ latest data."""
        if not self.is_trained:
            raise ValueError("Model chưa được train!")

        X_seq, _ = self.sequence_builder.transform(X)
        y_scaled = self.model.predict(X_seq, verbose=0).flatten()
        return self.sequence_builder.inverse_transform_target(y_scaled)

    def predict_with_confidence(
        self, X: pd.DataFrame, n_estimators_range: int = 50
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Predict với confidence interval."""
        predictions = self.predict(X)
        rmse = self.train_metrics.get("rmse", 0)
        lower = predictions - 1.96 * rmse
        upper = predictions + 1.96 * rmse
        return predictions, lower, upper

    def evaluate(self, X_test: pd.DataFrame, y_test: pd.Series) -> dict:
        """Evaluate trên test set (override để handle sequences)."""
        if not self.is_trained:
            raise ValueError("Model chưa được train!")

        X_seq, y_seq = self.sequence_builder.transform(X_test, y_test)
        if len(X_seq) == 0:
            return {"mae": 999, "rmse": 999, "r2": -999, "mape": 999}

        y_pred_scaled = self.model.predict(X_seq, verbose=0).flatten()
        y_pred = self.sequence_builder.inverse_transform_target(y_pred_scaled)
        y_true = self.sequence_builder.inverse_transform_target(y_seq)

        return self._eval_regression(y_true, y_pred)

    def save(self, suffix: str = "") -> str:
        """Save LSTM model (Keras native, không dùng joblib)."""
        if not self.is_trained:
            raise ValueError("Model chưa được train!")

        # Save Keras model
        model_dir = MODELS_DIR / f"{self.name}{suffix}"
        model_dir.mkdir(exist_ok=True)
        
        model_path = model_dir / "model.keras"
        self.model.save(str(model_path))

        # Save scalers + metadata
        scalers_path = model_dir / "scalers.joblib"
        self.sequence_builder.save_scalers(str(scalers_path))

        # Save metadata
        import joblib
        meta_path = model_dir / "metadata.joblib"
        joblib.dump({
            "name": self.name,
            "model_type": self.model_type,
            "feature_names": self.feature_names,
            "train_metrics": self.train_metrics,
            "saved_at": datetime.now().isoformat(),
        }, str(meta_path))

        self.logger.info(f"LSTM model saved: {model_dir}")
        return str(model_dir)

    def load(self, filepath: str):
        """Load LSTM model."""
        from tensorflow.keras.models import load_model

        model_dir = Path(filepath)
        
        self.model = load_model(str(model_dir / "model.keras"))
        self.sequence_builder.load_scalers(str(model_dir / "scalers.joblib"))

        import joblib
        meta = joblib.load(str(model_dir / "metadata.joblib"))
        self.name = meta["name"]
        self.model_type = meta["model_type"]
        self.feature_names = meta["feature_names"]
        self.train_metrics = meta["train_metrics"]
        self.is_trained = True

        self.logger.info(f"LSTM model loaded: {model_dir}")


class LSTMTrendModel(BaseModel):
    """LSTM cho dự đoán trend (classification)."""

    def __init__(self, horizon: str = "7d"):
        super().__init__(f"lstm_trend_{horizon}", model_type="classification")
        self.horizon = horizon
        self.sequence_builder = SequenceBuilder(sequence_length=LSTM_SEQUENCE_LENGTH)

    def _build_model(self, n_features: int):
        """Build LSTM classifier."""
        from tensorflow.keras.models import Sequential
        from tensorflow.keras.layers import LSTM, Dense, Dropout
        from tensorflow.keras.optimizers import Adam

        model = Sequential([
            LSTM(64, return_sequences=True,
                 input_shape=(LSTM_SEQUENCE_LENGTH, n_features)),
            Dropout(0.2),
            LSTM(32, return_sequences=False),
            Dropout(0.2),
            Dense(16, activation="relu"),
            Dense(3, activation="softmax"),  # 3 classes: Giảm, Sideway, Tăng
        ])

        model.compile(
            optimizer=Adam(learning_rate=0.001),
            loss="sparse_categorical_crossentropy",
            metrics=["accuracy"],
        )
        return model

    def train(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: Optional[pd.DataFrame] = None,
        y_val: Optional[pd.Series] = None,
        **kwargs,
    ):
        """Train LSTM classifier."""
        from tensorflow.keras.callbacks import EarlyStopping

        self.feature_names = list(X_train.columns)

        # For classification, scale features but NOT target
        X_scaled = self.sequence_builder.feature_scaler.fit_transform(X_train.values)
        self.sequence_builder.is_fitted = True

        # Create sequences manually (target is class label, no scaling)
        sequences, targets = [], []
        seq_len = self.sequence_builder.sequence_length
        y_arr = y_train.values

        for i in range(seq_len, len(X_scaled)):
            sequences.append(X_scaled[i - seq_len:i])
            targets.append(y_arr[i])

        X_seq = np.array(sequences)
        y_seq = np.array(targets)

        self.model = self._build_model(X_seq.shape[2])

        callbacks = [
            EarlyStopping(patience=10, restore_best_weights=True),
        ]

        self.model.fit(
            X_seq, y_seq,
            epochs=kwargs.get("epochs", LSTM_EPOCHS),
            batch_size=kwargs.get("batch_size", LSTM_BATCH_SIZE),
            callbacks=callbacks,
            verbose=0,
        )

        self.is_trained = True
        y_pred = np.argmax(self.model.predict(X_seq, verbose=0), axis=1)
        self.train_metrics = self._eval_classification(y_seq.astype(int), y_pred)

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Predict trend class."""
        if not self.is_trained:
            raise ValueError("Model chưa được train!")

        X_scaled = self.sequence_builder.feature_scaler.transform(X.values)
        seq_len = self.sequence_builder.sequence_length

        if len(X_scaled) < seq_len:
            padding = np.zeros((seq_len - len(X_scaled), X_scaled.shape[1]))
            X_scaled = np.vstack([padding, X_scaled])

        X_seq = X_scaled[-seq_len:].reshape(1, seq_len, X_scaled.shape[1])
        proba = self.model.predict(X_seq, verbose=0)
        return np.argmax(proba, axis=1)

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Predict probability for each class."""
        if not self.is_trained:
            raise ValueError("Model chưa được train!")

        X_scaled = self.sequence_builder.feature_scaler.transform(X.values)
        seq_len = self.sequence_builder.sequence_length

        if len(X_scaled) < seq_len:
            padding = np.zeros((seq_len - len(X_scaled), X_scaled.shape[1]))
            X_scaled = np.vstack([padding, X_scaled])

        X_seq = X_scaled[-seq_len:].reshape(1, seq_len, X_scaled.shape[1])
        return self.model.predict(X_seq, verbose=0)

    def save(self, suffix: str = "") -> str:
        """Save LSTM trend model (same Keras pattern)."""
        if not self.is_trained:
            raise ValueError("Model chưa được train!")

        model_dir = MODELS_DIR / f"{self.name}{suffix}"
        model_dir.mkdir(exist_ok=True)

        self.model.save(str(model_dir / "model.keras"))

        import joblib
        joblib.dump({
            "feature_scaler": self.sequence_builder.feature_scaler,
            "sequence_length": self.sequence_builder.sequence_length,
        }, str(model_dir / "scalers.joblib"))

        joblib.dump({
            "name": self.name,
            "model_type": self.model_type,
            "feature_names": self.feature_names,
            "train_metrics": self.train_metrics,
            "saved_at": datetime.now().isoformat(),
        }, str(model_dir / "metadata.joblib"))

        self.logger.info(f"LSTM trend model saved: {model_dir}")
        return str(model_dir)

    def load(self, filepath: str):
        """Load LSTM trend model."""
        from tensorflow.keras.models import load_model
        import joblib

        model_dir = Path(filepath)
        self.model = load_model(str(model_dir / "model.keras"))

        scalers = joblib.load(str(model_dir / "scalers.joblib"))
        self.sequence_builder.feature_scaler = scalers["feature_scaler"]
        self.sequence_builder.sequence_length = scalers["sequence_length"]
        self.sequence_builder.is_fitted = True

        meta = joblib.load(str(model_dir / "metadata.joblib"))
        self.name = meta["name"]
        self.feature_names = meta["feature_names"]
        self.train_metrics = meta["train_metrics"]
        self.is_trained = True
