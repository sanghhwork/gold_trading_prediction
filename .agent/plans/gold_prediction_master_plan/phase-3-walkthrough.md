# Phase 3 Walkthrough: Feature Engineering

**Plan:** Gold Prediction Master Plan
**Ngày triển khai:** 2026-03-22
**Trạng thái:** ✅ Hoàn thành

---

## 📋 Kết quả Feature Engineering

### Feature Matrix
- **Shape:** 1252 rows × 103 columns (92 features + 9 targets + date + source)
- **Train data sẵn sàng:** X=(1245, 92), 0 NaN

### Feature Breakdown

| Category | Count | Ví dụ |
|----------|-------|-------|
| Technical | 30 | SMA(20,50,200), EMA(12,26), RSI, MACD, BB, ATR, Stochastic, Williams %R, OBV, crossovers |
| Macro | 16 | DXY, Oil, USD/VND, US 10Y changes, Gold/DXY ratio, Gold/Oil ratio, DXY RSI |
| Calendar | 7 | day_of_week, month, quarter, is_month_start/end, week_of_year |
| Lag/Rolling | 31 | close/high/low/volume lags (1,5,10,20d), rolling mean/std/max/min (5,10,20d) |
| Return/Vol | 9 | returns (1,5,20d), cumulative 20d return, volatility 5d/20d |
| **Targets** | **9** | price/trend/return × 1d/7d/30d |

### Target Distribution (7 ngày)
- 🟢 Tăng (2): 632 samples (50.8%)
- 🔴 Giảm (0): 407 samples (32.7%)
- 🟡 Sideway (1): 206 samples (16.5%)

---

## 📁 Files Created

| File | Description |
|------|-------------|
| `backend/app/services/feature_engine/technical_indicators.py` | 30 technical indicators (SMA, EMA, RSI, MACD, BB, ATR...) |
| `backend/app/services/feature_engine/macro_features.py` | 16 macro features (cross-asset ratios, DXY RSI) |
| `backend/app/services/feature_engine/feature_builder.py` | Pipeline orchestrator + target generation |

---

## ➡️ Next: Phase 4 - ML Models
- Price prediction (XGBoost, LSTM, Prophet)
- Trend classification (XGBoost, LSTM)
- Ensemble model
