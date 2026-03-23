"""
Tests for Data Collectors V2.
Test sentiment analyzer, fear & greed collector, FRED collector.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest


class TestSentimentAnalyzer:
    """Test sentiment analysis."""

    @pytest.fixture
    def analyzer(self):
        from app.services.data_collector.sentiment_analyzer import SentimentAnalyzer
        return SentimentAnalyzer()

    def test_bullish_detection(self, analyzer):
        result = analyzer.analyze_text("Gold price surges to all-time high amid demand")
        assert result["score"] > 0
        assert result["label"] == "bullish"

    def test_bearish_detection(self, analyzer):
        result = analyzer.analyze_text("Gold drops sharply as dollar rises, investors sell off")
        assert result["score"] < 0
        assert result["label"] == "bearish"

    def test_neutral_detection(self, analyzer):
        result = analyzer.analyze_text("Meeting discussed economic outlook today")
        assert result["label"] == "neutral"
        assert result["score"] == 0.0

    def test_score_range(self, analyzer):
        """Score must be in [-1, 1]."""
        for text in ["gold rises 500%", "gold crashes completely", "normal day"]:
            result = analyzer.analyze_text(text)
            assert -1.0 <= result["score"] <= 1.0, f"Score {result['score']} out of range"

    def test_label_valid(self, analyzer):
        """Label must be bullish/bearish/neutral."""
        result = analyzer.analyze_text("Gold test text")
        assert result["label"] in ("bullish", "bearish", "neutral")

    def test_vietnamese_keywords(self, analyzer):
        """Vietnamese keyword detection."""
        result = analyzer.analyze_text("Vàng tăng mạnh kỷ lục")
        assert result["score"] > 0

    def test_empty_text(self, analyzer):
        result = analyzer.analyze_text("")
        assert result["label"] == "neutral"


class TestFearGreedCollector:
    """Test Fear & Greed Index collector."""

    @pytest.fixture
    def collector(self):
        from app.services.data_collector.fear_greed_collector import FearGreedCollector
        return FearGreedCollector()

    def test_fetch_data(self, collector):
        """API returns data (may be empty if already up to date)."""
        df = collector.fetch_data()
        import pandas as pd
        # May be empty if DB already has today's data (incremental)
        assert isinstance(df, pd.DataFrame)
        if not df.empty:
            assert "date" in df.columns
            assert "close" in df.columns

    def test_values_range(self, collector):
        """Values should be 0-100."""
        df = collector.fetch_data()
        if not df.empty:
            assert df["close"].min() >= 0
            assert df["close"].max() <= 100

    def test_dates_valid(self, collector):
        """Dates are in proper format."""
        df = collector.fetch_data()
        if not df.empty:
            import pandas as pd
            for d in df["date"].head():
                pd.Timestamp(d)  # Should not raise


class TestFREDCollector:
    """Test FRED collector."""

    def test_init_without_key(self):
        """Collector initializes even without API key."""
        from app.services.data_collector.fred_collector import FREDCollector
        fc = FREDCollector()
        # Should not error, just log warning

    def test_graceful_no_key(self):
        """collect_and_store returns 0 without API key."""
        from app.services.data_collector.fred_collector import FREDCollector
        import os
        # Ensure no key
        old_key = os.environ.pop("FRED_API_KEY", None)
        fc = FREDCollector()
        if not fc.api_key:
            result = fc.collect_and_store()
            assert result == 0
        if old_key:
            os.environ["FRED_API_KEY"] = old_key


class TestConstants:
    """Test V2 constants."""

    def test_gld_ticker(self):
        from app.utils.constants import ALL_YFINANCE_TICKERS
        assert "gld_etf" in ALL_YFINANCE_TICKERS

    def test_embargo_days(self):
        from app.utils.constants import EMBARGO_DAYS
        assert EMBARGO_DAYS >= 1

    def test_prediction_horizons(self):
        from app.utils.constants import PREDICTION_HORIZONS
        assert "1d" in PREDICTION_HORIZONS
        assert "7d" in PREDICTION_HORIZONS
        assert "30d" in PREDICTION_HORIZONS


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
