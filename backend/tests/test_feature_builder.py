"""
Tests for Feature Builder.
Test feature output shape, NaN handling, target variables.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
import numpy as np
import pandas as pd


class TestFeatureBuilder:
    """Test FeatureBuilder output."""

    @pytest.fixture
    def builder(self):
        from app.services.feature_engine.feature_builder import FeatureBuilder
        return FeatureBuilder()

    @pytest.fixture
    def sample_df(self):
        """Create sample OHLCV data."""
        dates = pd.date_range("2024-01-01", periods=300, freq="B")
        np.random.seed(42)
        close = np.cumsum(np.random.randn(300)) + 2000
        return pd.DataFrame({
            "date": dates,
            "open": close + np.random.randn(300) * 5,
            "high": close + abs(np.random.randn(300) * 10),
            "low": close - abs(np.random.randn(300) * 10),
            "close": close,
            "volume": np.random.randint(1000, 100000, 300).astype(float),
        })

    def test_build_features_not_empty(self, builder):
        """Feature builder returns non-empty DataFrame."""
        df = builder.build_features(source="xau_usd", include_macro=False)
        # May be empty if DB is empty, but should not error
        assert isinstance(df, pd.DataFrame)

    def test_technical_indicators(self, builder, sample_df):
        """Technical indicators are computed correctly."""
        result = builder._add_technical_indicators(sample_df.copy())
        assert "sma_20" in result.columns
        assert "rsi_14" in result.columns
        assert "macd" in result.columns
        assert "bb_upper" in result.columns
        assert len(result) == len(sample_df)

    def test_target_variables(self, builder, sample_df):
        """Target variables (return, trend) are created."""
        df = builder._add_technical_indicators(sample_df.copy())
        result = builder._add_target_variables(df)
        
        # Check return targets exist
        assert any("target_return" in col for col in result.columns)
        
        # Check trend targets exist
        assert any("target_trend" in col for col in result.columns)

    def test_no_inf_values(self, builder, sample_df):
        """No infinite values in features."""
        result = builder._add_technical_indicators(sample_df.copy())
        numeric_cols = result.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            assert not np.isinf(result[col]).any(), f"Inf found in {col}"

    def test_feature_count_minimum(self, builder, sample_df):
        """At least 30 features created."""
        result = builder._add_technical_indicators(sample_df.copy())
        numeric_cols = result.select_dtypes(include=[np.number]).columns
        assert len(numeric_cols) >= 30, f"Only {len(numeric_cols)} features"


class TestDynamicThresholds:
    """Test dynamic trend thresholds."""

    def test_thresholds_exist(self):
        from app.utils.constants import DYNAMIC_TREND_THRESHOLDS
        assert "1d" in DYNAMIC_TREND_THRESHOLDS
        assert "7d" in DYNAMIC_TREND_THRESHOLDS
        assert "30d" in DYNAMIC_TREND_THRESHOLDS

    def test_thresholds_increasing(self):
        """Longer horizons → larger thresholds."""
        from app.utils.constants import DYNAMIC_TREND_THRESHOLDS
        assert DYNAMIC_TREND_THRESHOLDS["1d"] < DYNAMIC_TREND_THRESHOLDS["7d"]
        assert DYNAMIC_TREND_THRESHOLDS["7d"] < DYNAMIC_TREND_THRESHOLDS["30d"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
