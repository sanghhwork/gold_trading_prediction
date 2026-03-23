"""
Tests for Backtester & Risk Metrics.
Test backtest engine, metrics calculation, risk metrics.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
import numpy as np
import pandas as pd


class TestRiskMetrics:
    """Test risk metrics calculations."""

    @pytest.fixture
    def positive_returns(self):
        """Mostly positive returns."""
        np.random.seed(42)
        return np.random.normal(0.002, 0.01, 252).tolist()

    @pytest.fixture
    def negative_returns(self):
        """Mostly negative returns."""
        np.random.seed(42)
        return np.random.normal(-0.002, 0.01, 252).tolist()

    @pytest.fixture
    def zero_returns(self):
        """Zero returns."""
        return [0.0] * 252

    def test_sharpe_positive(self, positive_returns):
        from app.services.backtesting.risk_metrics import RiskMetrics
        rm = RiskMetrics(positive_returns)
        sharpe = rm.sharpe_ratio()
        assert sharpe > 0, "Positive returns should have positive Sharpe"

    def test_sharpe_negative(self, negative_returns):
        from app.services.backtesting.risk_metrics import RiskMetrics
        rm = RiskMetrics(negative_returns)
        sharpe = rm.sharpe_ratio()
        assert sharpe < 0, "Negative returns should have negative Sharpe"

    def test_sharpe_zero(self, zero_returns):
        from app.services.backtesting.risk_metrics import RiskMetrics
        rm = RiskMetrics(zero_returns)
        sharpe = rm.sharpe_ratio()
        assert sharpe == 0, "Zero returns should have zero Sharpe"

    def test_max_drawdown_bounded(self, positive_returns):
        from app.services.backtesting.risk_metrics import RiskMetrics
        rm = RiskMetrics(positive_returns)
        mdd = rm.max_drawdown()
        assert 0 <= mdd <= 1, f"Max drawdown should be [0,1], got {mdd}"

    def test_var_bounded(self, positive_returns):
        from app.services.backtesting.risk_metrics import RiskMetrics
        rm = RiskMetrics(positive_returns)
        var = rm.value_at_risk(0.95)
        assert var >= 0, "VaR should be non-negative"

    def test_cvar_gte_var(self, positive_returns):
        from app.services.backtesting.risk_metrics import RiskMetrics
        rm = RiskMetrics(positive_returns)
        var = rm.value_at_risk(0.95)
        cvar = rm.conditional_var(0.95)
        assert cvar >= var, "CVaR should be >= VaR"

    def test_summary_keys(self, positive_returns):
        from app.services.backtesting.risk_metrics import RiskMetrics
        rm = RiskMetrics(positive_returns)
        s = rm.summary()
        expected_keys = ["sharpe_ratio", "sortino_ratio", "max_drawdown_pct",
                        "calmar_ratio", "var_95_pct", "cvar_95_pct", "volatility_ann_pct"]
        for key in expected_keys:
            assert key in s, f"Missing key: {key}"


class TestBacktester:
    """Test backtester engine."""

    @pytest.fixture
    def simulated_data(self):
        """Simulated predictions + prices."""
        np.random.seed(42)
        dates = pd.date_range("2025-01-01", periods=100, freq="B")
        prices = pd.Series(np.cumsum(np.random.randn(100) * 10) + 2000, index=dates)
        predictions = pd.DataFrame({
            "date": dates,
            "predicted_trend": np.random.choice([0, 1, 2], size=100),
            "predicted_return": np.random.randn(100) * 2,
        })
        return predictions, prices

    def test_backtest_returns_dict(self, simulated_data):
        from app.services.backtesting.backtester import Backtester
        predictions, prices = simulated_data
        bt = Backtester(initial_capital=100_000)
        results = bt.backtest(predictions, prices, horizon="7d")
        
        assert "metrics" in results
        assert "equity_curve" in results
        assert "trades" in results

    def test_backtest_metrics_keys(self, simulated_data):
        from app.services.backtesting.backtester import Backtester
        predictions, prices = simulated_data
        bt = Backtester(initial_capital=100_000)
        results = bt.backtest(predictions, prices)
        
        metrics = results["metrics"]
        assert "total_return_pct" in metrics
        assert "sharpe_ratio" in metrics
        assert "max_drawdown_pct" in metrics
        assert "win_rate_pct" in metrics

    def test_backtest_equity_curve(self, simulated_data):
        from app.services.backtesting.backtester import Backtester
        predictions, prices = simulated_data
        bt = Backtester(initial_capital=100_000)
        results = bt.backtest(predictions, prices)
        
        curve = results["equity_curve"]
        assert len(curve) > 0
        assert curve[0]["equity"] == 100_000  # Start with initial capital

    def test_backtest_trades_structure(self, simulated_data):
        from app.services.backtesting.backtester import Backtester
        predictions, prices = simulated_data
        bt = Backtester(initial_capital=100_000)
        results = bt.backtest(predictions, prices)
        
        for trade in results["trades"]:
            assert "entry_date" in trade
            assert "exit_date" in trade
            assert "direction" in trade
            assert trade["direction"] in ["LONG", "SHORT"]


class TestBacktestReport:
    """Test report generator."""

    def test_text_report(self):
        from app.services.backtesting.backtest_report import BacktestReportGenerator
        rg = BacktestReportGenerator()
        results = {
            "metrics": {
                "initial_capital": 100_000,
                "final_capital": 105_000,
                "total_return_pct": 5.0,
                "sharpe_ratio": 1.5,
                "max_drawdown_pct": 3.0,
                "total_trades": 10,
                "win_rate_pct": 60,
            },
            "trades": [],
        }
        report = rg.generate_text_report(results)
        assert "BACKTEST REPORT" in report
        assert "105,000" in report

    def test_json_report(self):
        from app.services.backtesting.backtest_report import BacktestReportGenerator
        rg = BacktestReportGenerator()
        results = {"metrics": {"initial_capital": 100_000}, "equity_curve": [], "trades": []}
        json_report = rg.generate_json_report(results)
        assert "performance" in json_report
        assert "risk" in json_report


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
