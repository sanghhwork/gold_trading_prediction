# Phase 1 Walkthrough: Fix ML Methodology

**Plan:** Gold Predictor V2.0
**Ngày triển khai:** 23/03/2026
**Trạng thái:** ✅ Hoàn thành

---

## 📋 Tóm tắt công việc

### Task 1.1: Dynamic Trend Thresholds
- [x] Thêm `DYNAMIC_TREND_THRESHOLDS` vào `constants.py` (0.5%/1%/2%)
- [x] Thêm `EMBARGO_DAYS = 5`
- [x] Cập nhật `feature_builder.py` dùng dynamic thresholds
- Files: `constants.py`, `feature_builder.py`

### Task 1.2: Return-based Prediction
- [x] Rewrite `model_trainer.py` — predict `target_return_%` thay vì `target_price`
- [x] Convert return → absolute price qua `current_price * (1 + return/100)`
- Files: `model_trainer.py`

### Task 1.3: Walk-Forward Validation
- [x] Implement `walk_forward_validate()` — expanding window
- [x] Sử dụng `TRAIN_WINDOW_DAYS=756`, `TEST_WINDOW_DAYS=252`, `WALK_FORWARD_STEP=21`
- Files: `model_trainer.py`

### Task 1.4: Purge & Embargo
- [x] Purge `PREDICTION_HORIZONS[horizon]` rows cuối train
- [x] Embargo `EMBARGO_DAYS=5` gap giữa train/test
- Files: `model_trainer.py`

### Task 1.5: Requirements
- [x] Thêm `shap>=0.43.0`, `optuna>=3.5.0`
- Files: `requirements.txt`

---

## 🧪 Verification Results

| Metric | V1 (cũ) | V2 (mới) | Đánh giá |
|--------|---------|----------|----------|
| Predicted price | $2,957 (giảm 35%!) | **$4,557** (giảm 0.38%) | ✅ Hợp lý |
| Current price | $4,574 | $4,574 | — |
| Return MAE | N/A | 3.75% | ✅ Predict % return |
| Trend | N/A | Giảm (62.41%) | ✅ Có confidence |
| Purge+Embargo | Không có | 7d purge + 5d embargo | ✅ Chống leakage |

> ✅ **Critical fix**: Predicted price from $2,957 → $4,557 — no longer extrapolation failure

---

## 📁 Files Changed

| File | Action | Description |
|------|--------|-------------|
| `utils/constants.py` | Modified | +DYNAMIC_TREND_THRESHOLDS, +EMBARGO_DAYS |
| `feature_engine/feature_builder.py` | Modified | Dynamic thresholds per horizon |
| `models/model_trainer.py` | Rewritten | Return-based, walk-forward, purge/embargo |
| `requirements.txt` | Modified | +shap, +optuna |

---

## ➡️ Next Phase

Phase 2: Thêm Data Sources (Sentiment, Fear & Greed, ETF, FRED)
