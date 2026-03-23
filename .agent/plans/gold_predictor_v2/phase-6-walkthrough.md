# Phase 6 Walkthrough: Testing & Documentation

**Plan:** Gold Predictor V2.0
**Ngày triển khai:** 23/03/2026
**Trạng thái:** ✅ Hoàn thành

---

## 🧪 Unit Tests — 28 PASSED

### test_backtester.py (14 tests)
- RiskMetrics: Sharpe ±, VaR bounds, CVaR ≥ VaR, MaxDD ∈ [0,1]
- Backtester: structure, metrics keys, equity curve, trades
- BacktestReport: text + JSON generation

### test_collectors.py (14 tests)
- Sentiment: bullish/bearish/neutral/Vietnamese/empty/range
- Fear & Greed: fetch data, value range, dates
- FRED: init without key, graceful skip
- Constants: GLD ticker, embargo, horizons

### test_feature_builder.py (ready, needs training data)
- Technical indicators, target variables, NaN/Inf check

### test_model_trainer.py (ready, needs training data)
- Train all, predict, return-based pricing, model storage

---

## 📁 Files Changed

| File | Action |
|------|--------|
| `tests/__init__.py` | Existing |
| `tests/test_feature_builder.py` | NEW |
| `tests/test_model_trainer.py` | NEW |
| `tests/test_backtester.py` | NEW |
| `tests/test_collectors.py` | NEW |
| `requirements.txt` | +pytest |
