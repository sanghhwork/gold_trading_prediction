# Phase 4 Walkthrough: Backtesting Framework

**Plan:** Gold Predictor V2.0
**Ngày triển khai:** 23/03/2026
**Trạng thái:** ✅ Hoàn thành

---

## 📋 Tóm tắt

### Task 4.1: Backtester Engine
- [x] Walk-forward simulation (train → predict → execute → move window)
- [x] Position sizing: Fixed fraction + Kelly Criterion
- [x] Transaction costs (default 0.1%)
- [x] Equity curve tracking
- [x] Long/Short positions
- Files: `[NEW] backtesting/backtester.py`

### Task 4.2: Risk Metrics
- [x] Sharpe Ratio (annualized)
- [x] Sortino Ratio (downside risk)
- [x] Max Drawdown
- [x] Calmar Ratio
- [x] Value at Risk (Historical VaR 95%)
- [x] Conditional VaR / Expected Shortfall
- [x] Annualized Volatility
- Files: `[NEW] backtesting/risk_metrics.py`

### Task 4.3: Report Generator
- [x] Text report (human-readable, with emoji rating)
- [x] JSON report (structured, for API)
- [x] Trade history display
- Files: `[NEW] backtesting/backtest_report.py`

---

## 🧪 Verification (simulated data)

| Metric | Value |
|--------|-------|
| Sharpe Ratio | 0.63 |
| Sortino Ratio | 1.15 |
| Max Drawdown | 25.5% |
| VaR 95% | 2.89% |
| CVaR 95% | 3.60% |
| Volatility | 30.7% |
| Backtest trades | 21 |

---

## 📁 Files Changed

| File | Action | Description |
|------|--------|-------------|
| `backtesting/backtester.py` | NEW | Walk-forward backtest engine |
| `backtesting/risk_metrics.py` | NEW | Sharpe/Sortino/VaR/MaxDD |
| `backtesting/backtest_report.py` | NEW | Text + JSON reports |

---

## ➡️ Next Phase

Phase 5: API & Frontend Updates (new endpoints + dashboard)
