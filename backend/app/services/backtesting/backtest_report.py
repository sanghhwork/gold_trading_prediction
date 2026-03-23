"""
Gold Predictor - Backtest Report Generator
Tạo báo cáo backtest dễ đọc (text + JSON).

Điểm mở rộng tương lai:
- Thêm HTML report
- Thêm PDF export
- Thêm equity curve chart (matplotlib)
"""

from datetime import datetime
from typing import Optional

from app.utils.logger import get_logger

logger = get_logger(__name__)


class BacktestReportGenerator:
    """Generate human-readable backtest reports."""

    def __init__(self):
        self.logger = get_logger("backtest_report")

    def generate_text_report(self, results: dict) -> str:
        """Tạo text report từ backtest results."""
        metrics = results.get("metrics", {})
        trades = results.get("trades", [])

        lines = [
            "=" * 60,
            "📊 BACKTEST REPORT",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "=" * 60,
            "",
            "💰 PERFORMANCE",
            f"  Initial Capital:     ${metrics.get('initial_capital', 0):>12,.2f}",
            f"  Final Capital:       ${metrics.get('final_capital', 0):>12,.2f}",
            f"  Total Return:        {metrics.get('total_return_pct', 0):>11.2f}%",
            f"  Annualized Return:   {metrics.get('annualized_return_pct', 0):>11.2f}%",
            "",
            "📈 TRADING STATS",
            f"  Total Trades:        {metrics.get('total_trades', 0):>8}",
            f"  Winning Trades:      {metrics.get('winning_trades', 0):>8}",
            f"  Losing Trades:       {metrics.get('losing_trades', 0):>8}",
            f"  Win Rate:            {metrics.get('win_rate_pct', 0):>7.1f}%",
            f"  Avg Win:             {metrics.get('avg_win_pct', 0):>7.4f}%",
            f"  Avg Loss:            {metrics.get('avg_loss_pct', 0):>7.4f}%",
            f"  Profit Factor:       {metrics.get('profit_factor', 0):>8.2f}",
            f"  Avg Holding:         {metrics.get('avg_holding_days', 0):>6.1f} days",
            "",
            "🛡️ RISK METRICS",
            f"  Sharpe Ratio:        {metrics.get('sharpe_ratio', 0):>8.4f}",
            f"  Sortino Ratio:       {metrics.get('sortino_ratio', 0):>8.4f}",
            f"  Max Drawdown:        {metrics.get('max_drawdown_pct', 0):>7.2f}%",
            f"  Calmar Ratio:        {metrics.get('calmar_ratio', 0):>8.4f}",
            f"  VaR (95%):           {metrics.get('var_95', 0):>7.4f}%",
            f"  CVaR (95%):          {metrics.get('cvar_95', 0):>7.4f}%",
            "",
        ]

        # Rating
        sharpe = metrics.get("sharpe_ratio", 0)
        if sharpe > 2:
            rating = "⭐⭐⭐ EXCELLENT"
        elif sharpe > 1:
            rating = "⭐⭐ GOOD"
        elif sharpe > 0:
            rating = "⭐ MODERATE"
        else:
            rating = "❌ POOR"

        lines.extend([
            f"📋 OVERALL RATING: {rating}",
            "=" * 60,
        ])

        # Last 5 trades
        if trades:
            lines.extend(["", "📜 RECENT TRADES (last 5):"])
            for t in trades[-5:]:
                emoji = "🟢" if t["pnl_pct"] > 0 else "🔴"
                lines.append(
                    f"  {emoji} {t['direction']:<5} "
                    f"${t['entry_price']:>9,.2f} → ${t['exit_price']:>9,.2f} "
                    f"({t['pnl_pct']:+.2f}%) "
                    f"[{t.get('days_held', '?')}d]"
                )

        report = "\n".join(lines)
        self.logger.info("Backtest report generated")
        return report

    def generate_json_report(self, results: dict) -> dict:
        """Tạo structured JSON report cho API response."""
        metrics = results.get("metrics", {})
        
        return {
            "generated_at": datetime.now().isoformat(),
            "performance": {
                "initial_capital": metrics.get("initial_capital"),
                "final_capital": metrics.get("final_capital"),
                "total_return_pct": metrics.get("total_return_pct"),
                "annualized_return_pct": metrics.get("annualized_return_pct"),
            },
            "trading": {
                "total_trades": metrics.get("total_trades"),
                "win_rate_pct": metrics.get("win_rate_pct"),
                "profit_factor": metrics.get("profit_factor"),
                "avg_holding_days": metrics.get("avg_holding_days"),
            },
            "risk": {
                "sharpe_ratio": metrics.get("sharpe_ratio"),
                "sortino_ratio": metrics.get("sortino_ratio"),
                "max_drawdown_pct": metrics.get("max_drawdown_pct"),
                "calmar_ratio": metrics.get("calmar_ratio"),
                "var_95_pct": metrics.get("var_95"),
                "cvar_95_pct": metrics.get("cvar_95"),
            },
            "equity_curve": results.get("equity_curve", []),
            "trades": results.get("trades", []),
        }
