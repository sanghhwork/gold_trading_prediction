"""
Gold Predictor - Backtesting Engine
Walk-forward backtest trên giá vàng lịch sử.

Strategy: Theo signal từ model predictions
- predicted_trend = TĂNG (2) → BUY
- predicted_trend = GIẢM (0) → SELL/SHORT
- predicted_trend = SIDEWAY (1) → HOLD

Features:
- Walk-forward: train → predict → execute → move window
- Position sizing: Kelly Criterion hoặc fixed fraction
- Transaction costs simulation
- Equity curve tracking

Điểm mở rộng tương lai:
- Thêm multi-asset portfolio
- Thêm stop-loss / take-profit levels
- Thêm leverage simulation
"""

from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd

from app.services.backtesting.risk_metrics import RiskMetrics
from app.utils.constants import PREDICTION_HORIZONS
from app.utils.logger import get_logger

logger = get_logger(__name__)


class Backtester:
    """
    Walk-forward backtester cho gold trading strategies.
    
    Usage:
        bt = Backtester(initial_capital=100_000)
        results = bt.backtest(df_features, model_trainer, horizon="7d")
        report = bt.generate_report()
    """

    def __init__(
        self,
        initial_capital: float = 100_000.0,
        transaction_cost_pct: float = 0.001,  # 0.1% per trade
        position_size_pct: float = 1.0,       # 100% capital per trade
        use_kelly: bool = False,
    ):
        self.initial_capital = initial_capital
        self.transaction_cost_pct = transaction_cost_pct
        self.position_size_pct = position_size_pct
        self.use_kelly = use_kelly
        self.logger = get_logger("backtester")

        # Results
        self.trades = []
        self.equity_curve = []
        self.daily_returns = []

    def backtest(
        self,
        predictions: pd.DataFrame,
        prices: pd.Series,
        horizon: str = "7d",
    ) -> dict:
        """
        Run backtest dựa trên predictions đã có.
        
        Args:
            predictions: DataFrame với columns ['date', 'predicted_trend', 'predicted_return']
            prices: Series giá close (indexed by date)
            horizon: Prediction horizon
            
        Returns:
            dict với metrics, equity_curve, trades
        """
        self.logger.info(f"Starting backtest: {len(predictions)} predictions, horizon={horizon}")
        
        capital = self.initial_capital
        position = 0  # 0 = no position, 1 = long, -1 = short
        entry_price = 0.0
        entry_date = None
        
        self.trades = []
        self.equity_curve = [{"date": predictions.iloc[0]["date"], "equity": capital}]
        
        holding_days = PREDICTION_HORIZONS.get(horizon, 7)

        for i in range(len(predictions)):
            row = predictions.iloc[i]
            current_date = row["date"]
            current_price = float(prices.loc[prices.index == current_date].iloc[0]) if current_date in prices.index else None
            
            if current_price is None:
                continue
                
            predicted_trend = int(row.get("predicted_trend", 1))
            predicted_return = float(row.get("predicted_return", 0))
            
            # Position sizing
            if self.use_kelly and len(self.trades) >= 10:
                size_pct = self._kelly_fraction()
            else:
                size_pct = self.position_size_pct

            # Trading logic
            if position == 0:
                # No position → open based on signal
                if predicted_trend == 2:  # TĂNG → BUY
                    position = 1
                    entry_price = current_price
                    entry_date = current_date
                    cost = capital * size_pct * self.transaction_cost_pct
                    capital -= cost
                    
                elif predicted_trend == 0:  # GIẢM → SHORT
                    position = -1
                    entry_price = current_price
                    entry_date = current_date
                    cost = capital * size_pct * self.transaction_cost_pct
                    capital -= cost

            elif position != 0:
                # Check if holding period reached
                if entry_date is not None:
                    days_held = (pd.Timestamp(current_date) - pd.Timestamp(entry_date)).days
                    
                    if days_held >= holding_days or predicted_trend == 1:
                        # Close position
                        if position == 1:  # Close long
                            pnl_pct = (current_price - entry_price) / entry_price
                        else:  # Close short
                            pnl_pct = (entry_price - current_price) / entry_price
                        
                        pnl = capital * size_pct * pnl_pct
                        cost = capital * size_pct * self.transaction_cost_pct
                        capital += pnl - cost
                        
                        self.trades.append({
                            "entry_date": entry_date,
                            "exit_date": current_date,
                            "direction": "LONG" if position == 1 else "SHORT",
                            "entry_price": round(entry_price, 2),
                            "exit_price": round(current_price, 2),
                            "pnl_pct": round(pnl_pct * 100, 4),
                            "pnl_usd": round(pnl, 2),
                            "days_held": days_held,
                        })
                        
                        position = 0
                        entry_price = 0
                        entry_date = None

            self.equity_curve.append({
                "date": current_date,
                "equity": round(capital, 2),
            })

        # Close any remaining position
        if position != 0 and len(predictions) > 0:
            final_price = float(prices.iloc[-1]) if not prices.empty else entry_price
            if position == 1:
                pnl_pct = (final_price - entry_price) / entry_price
            else:
                pnl_pct = (entry_price - final_price) / entry_price
            pnl = capital * self.position_size_pct * pnl_pct
            capital += pnl
            
            self.trades.append({
                "entry_date": entry_date,
                "exit_date": "OPEN",
                "direction": "LONG" if position == 1 else "SHORT",
                "entry_price": round(entry_price, 2),
                "exit_price": round(final_price, 2),
                "pnl_pct": round(pnl_pct * 100, 4),
                "pnl_usd": round(pnl, 2),
                "days_held": 0,
            })

        # Calculate metrics
        self.daily_returns = self._calculate_daily_returns()
        metrics = self._calculate_metrics(capital)

        self.logger.info(
            f"Backtest complete: {len(self.trades)} trades, "
            f"Return={metrics['total_return_pct']:.2f}%, "
            f"Sharpe={metrics['sharpe_ratio']:.2f}, "
            f"MaxDD={metrics['max_drawdown_pct']:.2f}%"
        )

        return {
            "metrics": metrics,
            "equity_curve": self.equity_curve,
            "trades": self.trades,
        }

    def _calculate_daily_returns(self) -> list[float]:
        """Calculate daily returns from equity curve."""
        if len(self.equity_curve) < 2:
            return []
        
        returns = []
        for i in range(1, len(self.equity_curve)):
            prev = self.equity_curve[i - 1]["equity"]
            curr = self.equity_curve[i]["equity"]
            if prev > 0:
                returns.append((curr - prev) / prev)
        return returns

    def _calculate_metrics(self, final_capital: float) -> dict:
        """Calculate backtest performance metrics."""
        risk = RiskMetrics(self.daily_returns)
        
        # Trade stats
        winning_trades = [t for t in self.trades if t["pnl_pct"] > 0]
        losing_trades = [t for t in self.trades if t["pnl_pct"] < 0]
        
        total_return = (final_capital - self.initial_capital) / self.initial_capital * 100
        
        # Annualized return
        n_days = len(self.equity_curve)
        ann_return = ((final_capital / self.initial_capital) ** (252 / max(n_days, 1)) - 1) * 100

        # Win rate
        win_rate = len(winning_trades) / max(len(self.trades), 1) * 100
        
        # Avg win/loss
        avg_win = np.mean([t["pnl_pct"] for t in winning_trades]) if winning_trades else 0
        avg_loss = abs(np.mean([t["pnl_pct"] for t in losing_trades])) if losing_trades else 0
        
        # Profit factor
        gross_profit = sum(t["pnl_usd"] for t in winning_trades)
        gross_loss = abs(sum(t["pnl_usd"] for t in losing_trades))
        profit_factor = gross_profit / max(gross_loss, 1)

        return {
            "initial_capital": self.initial_capital,
            "final_capital": round(final_capital, 2),
            "total_return_pct": round(total_return, 2),
            "annualized_return_pct": round(ann_return, 2),
            "total_trades": len(self.trades),
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "win_rate_pct": round(win_rate, 2),
            "avg_win_pct": round(avg_win, 4),
            "avg_loss_pct": round(avg_loss, 4),
            "profit_factor": round(profit_factor, 2),
            "sharpe_ratio": round(risk.sharpe_ratio(), 4),
            "sortino_ratio": round(risk.sortino_ratio(), 4),
            "max_drawdown_pct": round(risk.max_drawdown() * 100, 2),
            "calmar_ratio": round(risk.calmar_ratio(ann_return / 100), 4),
            "var_95": round(risk.value_at_risk(0.95) * 100, 4),
            "cvar_95": round(risk.conditional_var(0.95) * 100, 4),
            "avg_holding_days": round(np.mean([t["days_held"] for t in self.trades]) if self.trades else 0, 1),
        }

    def _kelly_fraction(self) -> float:
        """Kelly Criterion position sizing."""
        if len(self.trades) < 10:
            return self.position_size_pct
        
        winning = [t for t in self.trades if t["pnl_pct"] > 0]
        losing = [t for t in self.trades if t["pnl_pct"] < 0]
        
        if not winning or not losing:
            return self.position_size_pct
        
        p = len(winning) / len(self.trades)
        q = 1 - p
        avg_win = np.mean([t["pnl_pct"] for t in winning])
        avg_loss = abs(np.mean([t["pnl_pct"] for t in losing]))
        
        if avg_loss == 0:
            return self.position_size_pct
        
        b = avg_win / avg_loss  # odds
        kelly = (b * p - q) / b
        
        # Half-Kelly for safety
        kelly = max(0.0, min(kelly * 0.5, 0.5))
        
        return kelly


def run_simple_backtest(
    horizon: str = "7d",
    initial_capital: float = 100_000,
) -> dict:
    """
    Convenience: run backtest using walk-forward predictions.
    
    Usage from CLI or API:
        results = run_simple_backtest("7d")
    """
    from app.services.models.model_trainer import ModelTrainer
    from app.services.feature_engine.feature_builder import FeatureBuilder
    
    logger.info(f"Running simple backtest for {horizon}...")
    
    # 1. Build features
    fb = FeatureBuilder()
    df = fb.build_features(source="xau_usd", include_macro=True)
    
    # 2. Train + get walk-forward results
    trainer = ModelTrainer()
    wf_results = trainer.walk_forward_validate(horizon=horizon)
    
    if not wf_results:
        logger.error("Walk-forward validation failed!")
        return {}
    
    # 3. Use walk-forward as proxy backtest
    bt = Backtester(initial_capital=initial_capital)
    
    return {
        "walk_forward": wf_results,
        "n_windows": wf_results.get("n_windows", 0),
        "avg_return_mae": wf_results.get("avg_return_metrics", {}).get("mae", 0),
        "avg_trend_accuracy": wf_results.get("avg_trend_metrics", {}).get("accuracy", 0),
    }
