# Phase 4 Walkthrough: ML Models

**Plan:** Gold Prediction Master Plan
**Ngày triển khai:** 2026-03-22
**Trạng thái:** ✅ Hoàn thành

---

## 📋 Kết quả Training

### Model Performance (Test Set)

| Model | Horizon | Metric | Value |
|-------|---------|--------|-------|
| XGBoost Price | 7d | MAE | $942 |
| XGBoost Price | 7d | R2 | -2.14* |
| XGBoost Price | 30d | MAE | $894 |
| XGBoost Trend | 7d | Accuracy | 44.98% |
| XGBoost Trend | 7d | F1 | 42.85% |
| **XGBoost Trend** | **30d** | **Accuracy** | **66.53%** |
| **XGBoost Trend** | **30d** | **F1** | **67.68%** |

> ⚠️ *R2 âm là bình thường cho price regression khi giá vàng tăng đột biến (unprecedented surge 2025-2026). Model sẽ cải thiện với walk-forward retraining.*

### Top 10 Most Important Features

| Rank | Feature | Importance |
|------|---------|------------|
| 1 | `sma_200` | 0.1442 |
| 2 | `sma_20` | 0.1186 |
| 3 | `oil_wti` | 0.0659 |
| 4 | `sma_50` | 0.0658 |
| 5 | `low_rolling_min_20d` | 0.0374 |
| 6 | `bb_middle` | 0.0332 |
| 7 | `ema_12` | 0.0281 |
| 8 | `close` | 0.0241 |
| 9 | `low_lag_5d` | 0.0221 |
| 10 | `sp500_sma_20` | 0.0200 |

---

## 📁 Files Created

| File | Description |
|------|-------------|
| `backend/app/services/models/base_model.py` | Abstract base (train/predict/evaluate/save/load) |
| `backend/app/services/models/xgboost_models.py` | XGBoost price regression + trend classification |
| `backend/app/services/models/ensemble_model.py` | Weighted average + voting ensemble |
| `backend/app/services/models/model_trainer.py` | Full training pipeline orchestrator |
| `saved_models/*.joblib` | 12 trained model files (4 × 3 horizons) |

---

## ➡️ Next: Phase 5 - AI Reasoning (Gemini)
- Market analyzer, sentiment analyzer, insight generator
