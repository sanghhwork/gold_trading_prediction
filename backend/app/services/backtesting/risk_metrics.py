"""
Gold Predictor - Risk Metrics Calculator
Tính toán các metrics rủi ro tiêu chuẩn cho backtesting.

Metrics:
- Sharpe Ratio: Risk-adjusted return (return/volatility)
- Sortino Ratio: Downside risk-adjusted return
- Max Drawdown: Largest peak-to-trough decline
- Calmar Ratio: Annual return / Max Drawdown
- Value at Risk (VaR): Maximum loss at confidence level
- Conditional VaR (CVaR/ES): Expected loss beyond VaR

Điểm mở rộng tương lai:
- Thêm Omega Ratio
- Thêm Information Ratio
- Thêm rolling metrics
"""

from typing import Optional

import numpy as np

from app.utils.logger import get_logger

logger = get_logger(__name__)


class RiskMetrics:
    """
    Risk metrics calculator cho financial returns.
    
    Usage:
        rm = RiskMetrics(daily_returns=[0.01, -0.005, 0.003, ...])
        sharpe = rm.sharpe_ratio()
        max_dd = rm.max_drawdown()
    """

    def __init__(self, returns: list[float], risk_free_rate: float = 0.04):
        """
        Args:
            returns: List daily returns (e.g., 0.01 = 1% gain)
            risk_free_rate: Annual risk-free rate (default: 4% US Treasury)
        """
        self.returns = np.array(returns) if returns else np.array([0.0])
        self.risk_free_rate = risk_free_rate
        self.daily_rf = risk_free_rate / 252  # Daily risk-free rate

    def sharpe_ratio(self, annualize: bool = True) -> float:
        """
        Sharpe Ratio = (mean_return - risk_free) / std_return
        
        > 1.0: Good
        > 2.0: Very Good
        > 3.0: Excellent
        """
        if len(self.returns) < 2 or np.std(self.returns) == 0:
            return 0.0

        excess_returns = self.returns - self.daily_rf
        sharpe = np.mean(excess_returns) / np.std(excess_returns, ddof=1)

        if annualize:
            sharpe *= np.sqrt(252)

        return float(sharpe)

    def sortino_ratio(self, annualize: bool = True) -> float:
        """
        Sortino Ratio = (mean_return - risk_free) / downside_std
        
        Tốt hơn Sharpe vì chỉ penalize downside volatility.
        """
        if len(self.returns) < 2:
            return 0.0

        excess_returns = self.returns - self.daily_rf
        downside_returns = excess_returns[excess_returns < 0]

        if len(downside_returns) == 0 or np.std(downside_returns) == 0:
            return 0.0 if np.mean(excess_returns) <= 0 else 999.0

        sortino = np.mean(excess_returns) / np.std(downside_returns, ddof=1)

        if annualize:
            sortino *= np.sqrt(252)

        return float(sortino)

    def max_drawdown(self) -> float:
        """
        Max Drawdown = largest peak-to-trough decline.
        
        Returns float (e.g., 0.15 = 15% drawdown).
        """
        if len(self.returns) < 1:
            return 0.0

        # Build equity curve
        cumulative = np.cumprod(1 + self.returns)
        running_max = np.maximum.accumulate(cumulative)
        drawdowns = (cumulative - running_max) / running_max

        return float(abs(np.min(drawdowns)))

    def calmar_ratio(self, annual_return: Optional[float] = None) -> float:
        """
        Calmar Ratio = Annualized Return / Max Drawdown
        
        > 1.0: Good
        > 3.0: Excellent
        """
        max_dd = self.max_drawdown()
        if max_dd == 0:
            return 0.0

        if annual_return is None:
            # Calculate from returns
            total_return = np.prod(1 + self.returns) - 1
            n_years = len(self.returns) / 252
            annual_return = (1 + total_return) ** (1 / max(n_years, 0.01)) - 1

        return float(annual_return / max_dd)

    def value_at_risk(self, confidence: float = 0.95) -> float:
        """
        Value at Risk: Maximum expected loss at given confidence level.
        
        Historical VaR (non-parametric).
        Returns positive number (e.g., 0.02 = 2% max daily loss at 95% confidence).
        """
        if len(self.returns) < 10:
            return 0.0

        percentile = (1 - confidence) * 100
        var = np.percentile(self.returns, percentile)
        return float(abs(var))

    def conditional_var(self, confidence: float = 0.95) -> float:
        """
        Conditional VaR (Expected Shortfall / CVaR):
        Average loss in worst (1-confidence)% of days.
        
        More conservative than VaR — accounts for tail risk.
        """
        if len(self.returns) < 10:
            return 0.0

        var = -self.value_at_risk(confidence)
        tail_returns = self.returns[self.returns <= var]

        if len(tail_returns) == 0:
            return self.value_at_risk(confidence)

        return float(abs(np.mean(tail_returns)))

    def volatility(self, annualize: bool = True) -> float:
        """Annualized volatility."""
        if len(self.returns) < 2:
            return 0.0

        vol = np.std(self.returns, ddof=1)
        if annualize:
            vol *= np.sqrt(252)
        return float(vol)

    def summary(self) -> dict:
        """Full risk metrics summary."""
        return {
            "sharpe_ratio": round(self.sharpe_ratio(), 4),
            "sortino_ratio": round(self.sortino_ratio(), 4),
            "max_drawdown_pct": round(self.max_drawdown() * 100, 2),
            "calmar_ratio": round(self.calmar_ratio(), 4),
            "var_95_pct": round(self.value_at_risk(0.95) * 100, 4),
            "cvar_95_pct": round(self.conditional_var(0.95) * 100, 4),
            "volatility_ann_pct": round(self.volatility() * 100, 2),
            "n_observations": len(self.returns),
        }
