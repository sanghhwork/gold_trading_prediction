"""
Tests for Model Trainer V2.
Test walk-forward, return prediction, multi-model ensemble.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
import numpy as np
import pandas as pd


class TestModelTrainer:
    """Test ModelTrainer V2."""

    @pytest.fixture
    def trainer(self):
        from app.services.models.model_trainer import ModelTrainer
        return ModelTrainer()

    def test_trainer_init(self, trainer):
        """Trainer initializes correctly."""
        assert trainer.trained_models == {}
        assert trainer.feature_cache is None

    def test_train_all_returns_dict(self, trainer):
        """train_all returns results dict with expected keys."""
        results = trainer.train_all(horizon="7d")
        assert isinstance(results, dict)
        assert "xgboost_return" in results
        assert "xgboost_trend" in results
        assert "lgbm_return" in results
        assert "lgbm_trend" in results

    def test_models_stored(self, trainer):
        """Trained models are stored in trainer."""
        trainer.train_all(horizon="7d")
        assert "7d" in trainer.trained_models
        models = trainer.trained_models["7d"]
        assert "xgb_price" in models
        assert "xgb_trend" in models
        assert "lgbm_price" in models
        assert "lgbm_trend" in models
        assert "ensemble_price" in models
        assert "ensemble_trend" in models

    def test_predict_returns_valid(self, trainer):
        """Prediction returns valid structure."""
        trainer.train_all(horizon="7d")
        pred = trainer.predict("7d")
        
        assert "predicted_price" in pred
        assert "predicted_return_pct" in pred
        assert "predicted_trend" in pred
        assert pred["predicted_price"] > 0
        assert pred["predicted_trend"] in [0, 1, 2]

    def test_return_based_prediction(self, trainer):
        """Price is derived from return, not predicted directly."""
        trainer.train_all(horizon="7d")
        pred = trainer.predict("7d")
        
        # Price should be reasonable (not extrapolated wildly)
        current = pred.get("current_price", 0)
        predicted = pred.get("predicted_price", 0)
        if current > 0:
            change_pct = abs(predicted - current) / current * 100
            assert change_pct < 50, f"Price change {change_pct:.1f}% too extreme"


class TestXGBoostModels:
    """Test XGBoost models."""

    def test_price_model(self):
        from app.services.models.xgboost_models import XGBoostPriceModel
        model = XGBoostPriceModel(horizon="7d")
        assert model.name == "xgboost_price_7d"
        assert model.model_type == "regression"
        assert not model.is_trained

    def test_trend_model(self):
        from app.services.models.xgboost_models import XGBoostTrendModel
        model = XGBoostTrendModel(horizon="7d")
        assert model.name == "xgboost_trend_7d"
        assert model.model_type == "classification"


class TestLightGBMModels:
    """Test LightGBM models."""

    def test_return_model(self):
        from app.services.models.lightgbm_models import LGBMReturnModel
        model = LGBMReturnModel(horizon="7d")
        assert model.name == "lgbm_return_7d"
        assert model.model_type == "regression"

    def test_trend_model(self):
        from app.services.models.lightgbm_models import LGBMTrendModel
        model = LGBMTrendModel(horizon="7d")
        assert model.name == "lgbm_trend_7d"
        assert model.model_type == "classification"


class TestEnsembleModel:
    """Test Ensemble model."""

    def test_ensemble_price(self):
        from app.services.models.ensemble_model import EnsemblePriceModel
        ens = EnsemblePriceModel(horizon="7d")
        assert ens.sub_models == []
        assert ens.weights == []

    def test_ensemble_add_model(self):
        from app.services.models.ensemble_model import EnsemblePriceModel
        from app.services.models.xgboost_models import XGBoostPriceModel
        
        ens = EnsemblePriceModel()
        xgb = XGBoostPriceModel()
        ens.add_model(xgb, weight=0.5)
        
        assert len(ens.sub_models) == 1
        assert ens.weights == [0.5]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
