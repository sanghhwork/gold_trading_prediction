# PLAN: Nâng cấp Gold Predictor - V2.0

> Dựa trên: `.agent/docs/project-evaluation.md`
> Ngày tạo: 23/03/2026
> Cập nhật: 23/03/2026 (theo review /review-plan — sửa 7 điểm)

---

## Mục tiêu

- Nâng điểm ML Methodology từ 5/10 → 8/10
- Nâng độ chính xác dự đoán trend từ ~50% → 60-65%
- Thêm Deep Learning (LSTM) cho price prediction (R² > 0.5)
- Thêm nguồn dữ liệu sentiment, fear & greed, ETF flows
- Có backtesting framework đo lường profitability thực tế
- Dashboard hiển thị đầy đủ: multiple models comparison, backtesting results

## Non-goals (chưa làm ở plan này)

- Triển khai production deployment (sẽ làm sau khi accuracy đạt yêu cầu)
- Premium SJC prediction riêng (cần 6+ tháng data SJC trước)
- Trading bot tự động (cần backtesting + paper trading trước)
- Mobile app

## Bối cảnh hiện trạng

### Codebase hiện tại
- **Models**: Chỉ XGBoost (price regression + trend classification)
- **Ensemble**: 1 model duy nhất (không phải ensemble thực sự)
- **Validation**: Simple 80/20 split (không walk-forward)
- **Prediction target**: Giá tuyệt đối (XGBoost không extrapolate được)
- **Data**: 92 features (technical + macro + calendar), thiếu sentiment
- **Backtesting**: Module rỗng (`backtesting/__init__.py`)
- **Tests**: Không có unit tests nào
- **Dependencies**: tensorflow, lightgbm đã có trong requirements.txt (chưa dùng), shap chưa có
- **Constants đã chuẩn bị** (`constants.py` line 75-82): Đã có sẵn `LSTM_SEQUENCE_LENGTH=60`, `LSTM_EPOCHS=100`, `TRAIN_WINDOW_DAYS=756`, `TEST_WINDOW_DAYS=252`, `WALK_FORWARD_STEP=21` — chưa được sử dụng
- **DB Schema sentiment** (`db/models.py` line 149-151): `NewsArticle` đã có `sentiment_score`, `sentiment_label`, `analyzed_at` — chưa được populate
- **Collectors**: 5 collectors (xau, sjc, giavang.org, macro, news) + `giavang_org_collector.py` mới nhất

### Files/modules liên quan chính

| File | Vai trò | Impact |
|------|---------|--------|
| `services/models/model_trainer.py` | Train orchestrator | Sửa lớn (walk-forward, return-based) |
| `services/models/xgboost_models.py` | XGBoost models | Sửa nhỏ (predict return) |
| `services/models/ensemble_model.py` | Ensemble container | Sửa lớn (thêm multi-model) |
| `services/models/base_model.py` | ABC save/load | Sửa trung bình (LSTM Keras save riêng) |
| `services/feature_engine/feature_builder.py` | 92 features | Sửa trung bình (thêm sentiment features) |
| `services/data_collector/data_pipeline.py` | Collector orchestrator | Sửa nhỏ (thêm collectors) |
| `services/backtesting/` | Rỗng | Viết mới toàn bộ |
| `api/routes/gold_routes.py` | API endpoints | Thêm endpoints mới |
| `utils/constants.py` | Params ML | Sửa nhỏ (dynamic threshold, verify params) |
| `config.py` + `.env` | App config | Sửa nhỏ (thêm FRED_API_KEY) |

---

## Thiết kế kỹ thuật - Chia theo 6 Phases

---

# PHASE 1: Fix ML Methodology (NGHIÊM TRỌNG - ƯU TIÊN CAO NHẤT)

> **Mục tiêu**: Sửa các lỗi methodology cơ bản để metrics đáng tin cậy
> **Effort ước lượng**: 8-10 giờ
> **Impact**: 🔴 Rất cao — Nền tảng cho mọi cải thiện sau này

### 1.1 Return-based Prediction thay vì Price Prediction

**Vấn đề**: XGBoost predict giá tuyệt đối → không extrapolate được vùng giá mới ($4,500+)

**Giải pháp**: Predict `% return` thay vì `price`, sau đó convert ngược lại giá.

```python
# HIỆN TẠI (sai):
target = future_close_price  # Model predict $2,957 khi data train max $3,500

# SAU KHI FIX:
target = (future_close / current_close - 1) * 100  # Model predict +2.3%
predicted_price = current_close * (1 + predicted_return/100)
```

**Thay đổi code**:
- `model_trainer.py`: Đổi y_target từ `target_price_{horizon}` sang `target_return_{horizon}`
- `xgboost_models.py`: XGBoostPriceModel → XGBoostReturnModel (rename + adjust output)
- Logic convert return → price trong `predict()` method
- `ensemble_model.py`: Tương tự — predict return rồi convert

### 1.2 Walk-Forward Validation

**Vấn đề**: Simple 80/20 split, chỉ 1 lần, không đo được variance hay out-of-sample robustness.

**Giải pháp**: Implement expanding window walk-forward validation.

> ⚠️ `constants.py` line 75-77 ĐÃ CÓ SẴN params — sử dụng trực tiếp:
> - `TRAIN_WINDOW_DAYS = 756` (3 năm trading days)
> - `TEST_WINDOW_DAYS = 252` (1 năm trading days)
> - `WALK_FORWARD_STEP = 21` (1 tháng)

```
Window 1: Train [=====756d=====]  Test [==252d==]
Window 2: Train [======777d======]  Test [==252d==]   (step +21d)
Window 3: Train [=======798d=======]  Test [==252d==]
...
→ Metrics = mean ± std across all windows
```

**Thay đổi code**:
- `model_trainer.py`: Thêm method `walk_forward_validate()` dùng expanding window
- Import `TRAIN_WINDOW_DAYS`, `TEST_WINDOW_DAYS`, `WALK_FORWARD_STEP` từ `constants.py`
- Return: `{ metrics_per_window[], avg_metrics, std_metrics }`
- Keep `train_all()` cho production training (full data), `walk_forward_validate()` cho evaluation

### 1.3 Purge & Embargo (Chống Data Leakage)

**Vấn đề**: Features dùng rolling window (SMA 200, RSI 14) tính trên toàn bộ dataset → overlap giữa train/test.

**Giải pháp**:
- **Purge**: Loại bỏ `horizon` rows cuối train set (vì target nhìn tới future)
- **Embargo**: Thêm N rows gap giữa train/test để tránh autocorrelation

**Thay đổi code**:
- `model_trainer.py`: Trong hàm split, áp dụng purge + embargo

```python
purge_size = PREDICTION_HORIZONS[horizon]  # 7 cho "7d"
embargo_size = 5  # thêm 5 ngày buffer

X_train = X.iloc[:split_idx - purge_size - embargo_size]
X_test = X.iloc[split_idx:]
```

### 1.4 Hyperparameter Tuning (Optuna)

**Thay đổi code**:
- `xgboost_models.py`: Thêm method `tune_hyperparameters(X, y, n_trials=50)`
- Sử dụng Optuna với TimeSeriesSplit
- Search space: n_estimators [100-1000], max_depth [3-10], learning_rate [0.01-0.3], subsample [0.6-1.0]
- Thêm `optuna` vào `requirements.txt`

### 1.5 Dynamic Trend Thresholds

> ⚠️ `constants.py` line 97-98 hiện dùng ±0.5% cho tất cả horizons.
> Thay đổi: Dùng threshold **tỷ lệ với horizon** để phân loại chính xác hơn.

```python
# HIỆN TẠI (constants.py):
TREND_THRESHOLD_UP = 0.005     # 0.5% cho mọi horizon
TREND_THRESHOLD_DOWN = -0.005

# SAU KHI FIX: Dynamic theo horizon
DYNAMIC_TREND_THRESHOLDS = {
    "1d": 0.005,   # ±0.5% cho 1 ngày
    "7d": 0.01,    # ±1.0% cho 1 tuần
    "30d": 0.02,   # ±2.0% cho 1 tháng
}
```

**Thay đổi code**:
- `constants.py`: Thêm `DYNAMIC_TREND_THRESHOLDS` dict
- `feature_builder.py`: `_add_target_variables()` dùng threshold theo horizon

### Files thay đổi Phase 1

| File | Hành động | Mô tả |
|------|-----------|-------|
| `services/models/model_trainer.py` | MODIFY | walk-forward, return prediction, purge/embargo |
| `services/models/xgboost_models.py` | MODIFY | Return-based target, optuna tuning |
| `services/models/ensemble_model.py` | MODIFY | Return-based prediction |
| `services/feature_engine/feature_builder.py` | MODIFY | Adjust get_train_data() + dynamic thresholds |
| `utils/constants.py` | MODIFY | Thêm DYNAMIC_TREND_THRESHOLDS, verify walk-forward params |
| `requirements.txt` | MODIFY | Thêm optuna, shap |


---

# PHASE 2: Thêm Data Sources

> **Mục tiêu**: Bổ sung 3-4 nguồn dữ liệu quan trọng nhất
> **Effort ước lượng**: 8-10 giờ
> **Impact**: 🔴 Cao — Thêm 30-40% thông tin thị trường

### 2.1 News Sentiment Collector (NLP)

**Hiện trạng**: `news_collector.py` chỉ crawl text từ cafef, chưa có sentiment analysis.

> ✅ **DB Schema đã sẵn sàng**: `NewsArticle` model (`db/models.py` line 149-151) ĐÃ CÓ:
> - `sentiment_score` (Float, -1.0 → +1.0)
> - `sentiment_label` (String: "bullish"/"bearish"/"neutral")
> - `analyzed_at` (DateTime)
> → Không cần sửa DB schema, chỉ cần tạo logic populate.

**Giải pháp**: Thêm sentiment pipeline:
- Dùng `transformers` + pre-trained model FinBERT hoặc PhoBERT (Vietnamese)
- Hoặc đơn giản hơn: dùng Gemini AI để phân tích sentiment (đã có client)
- Score: -1 (rất tiêu cực) → +1 (rất tích cực)
- Aggregate: daily average sentiment, sentiment volatility

**Files mới/sửa**:
- `[NEW] services/data_collector/sentiment_analyzer.py` — NLP pipeline
- `[MODIFY] services/data_collector/news_collector.py` — Gắn sentiment vào mỗi article (update `sentiment_score`, `sentiment_label`, `analyzed_at`)
- `[MODIFY] services/feature_engine/feature_builder.py` — Thêm sentiment features vào feature matrix

### 2.2 Fear & Greed Index Collector

**Nguồn**: `https://api.alternative.me/fng/?limit=30&format=json` (free, JSON)

**Dữ liệu**: `{ value: 0-100, value_classification: "Extreme Fear"/"Fear"/"Neutral"/"Greed"/"Extreme Greed" }`

**Files**:
- `[NEW] services/data_collector/fear_greed_collector.py`
- Lưu vào bảng `macro_indicators` có sẵn (indicator="fear_greed"), **không cần sửa DB schema**
- `[MODIFY] data_pipeline.py` — Tích hợp

### 2.3 ETF Flows (GLD Holdings)

**Nguồn**: Yahoo Finance ticker `GLD` (SPDR Gold Shares) — volume + AUM proxy

**Dữ liệu**: Volume (đại diện cho flows), giá GLD (đại diện cho holdings)

**Files**:
- `[MODIFY] services/data_collector/macro_collector.py` — Thêm ticker GLD
- `[MODIFY] services/feature_engine/macro_features.py` — Thêm GLD flow features

### 2.4 CPI/Inflation Data (FRED)

**Nguồn**: FRED API (`https://api.stlouisfed.org/fred/series/observations`) — free với API key

**Series**: `CPIAUCSL` (CPI All Items), `T5YIE` (5Y Breakeven Inflation), `DFEDTARU` (Fed Funds Rate)

**Files**:
- `[NEW] services/data_collector/fred_collector.py`
- Lưu vào bảng `macro_indicators` có sẵn (indicator="cpi"/"inflation_5y"/"fed_rate"), **không cần sửa DB schema**
- `[MODIFY] data_pipeline.py` — Tích hợp
- `[MODIFY] config.py` — Thêm `fred_api_key: str = ""`
- `[MODIFY] .env.example` — Thêm `FRED_API_KEY=your_key_here`

### Files thay đổi Phase 2

| File | Hành động | Mô tả |
|------|-----------|-------|
| `[NEW] services/data_collector/sentiment_analyzer.py` | NEW | NLP sentiment pipeline |
| `[NEW] services/data_collector/fear_greed_collector.py` | NEW | Fear & Greed Index |
| `[NEW] services/data_collector/fred_collector.py` | NEW | CPI, Inflation, Fed Rate |
| `services/data_collector/news_collector.py` | MODIFY | Populate sentiment_score/label đã có trong DB |
| `services/data_collector/macro_collector.py` | MODIFY | Thêm ticker GLD |
| `services/data_collector/data_pipeline.py` | MODIFY | Thêm 2 collectors mới |
| `services/feature_engine/feature_builder.py` | MODIFY | Thêm sentiment + FnG features |
| `services/feature_engine/macro_features.py` | MODIFY | Thêm GLD, CPI features |
| `config.py` | MODIFY | Thêm `fred_api_key` |
| `.env.example` | MODIFY | Thêm `FRED_API_KEY=` |
| `requirements.txt` | MODIFY | Thêm fredapi |

> ✅ **Không cần sửa `db/models.py`** — sentiment fields đã có trong `NewsArticle`, FnG/CPI dùng bảng `macro_indicators` có sẵn.

---

# PHASE 3: Deep Learning Models (LSTM/GRU)

> **Mục tiêu**: Thêm models có khả năng extrapolate cho price prediction
> **Effort ước lượng**: 8-10 giờ
> **Impact**: 🔴 Cao — R² có thể đạt 0.6-0.8

### 3.1 LSTM Price Model

**Lý do**: LSTM xử lý sequence data, có thể extrapolate (không bị giới hạn trong range training data như XGBoost).

**Kiến trúc**:

> ✅ `constants.py` line 80-82 ĐÃ CÓ sẵn LSTM params:
> - `LSTM_SEQUENCE_LENGTH = 60` (60 ngày lookback)
> - `LSTM_EPOCHS = 100`
> - `LSTM_BATCH_SIZE = 32`

```
Input: (batch, sequence_length=60, n_features)   # Dùng LSTM_SEQUENCE_LENGTH=60
    │
    ├── LSTM(64, return_sequences=True)
    ├── Dropout(0.2)
    ├── LSTM(32)
    ├── Dropout(0.2)
    ├── Dense(16, activation='relu')
    └── Dense(1)  # predicted return
```

> ⚠️ **LSTM Save/Load**: `base_model.py` dùng `joblib.dump()` — Keras model **KHÔNG tương thích** với joblib.
> → LSTM models cần override `save()`/`load()` để dùng `model.save('path.keras')` + `tf.keras.models.load_model()`.

**Files**:
- `[NEW] services/models/lstm_models.py` — LSTMReturnModel, LSTMTrendModel
- Kế thừa BaseModel interface (train, predict, **override save/load cho Keras**)
- Sequence preparation: sliding window `LSTM_SEQUENCE_LENGTH=60` days → predict return
- Scaler: MinMaxScaler cho features
- `[NEW] services/models/sequence_builder.py` — Tách riêng logic tạo sequences

### 3.2 LightGBM Models

**Lý do**: Diversity cho ensemble. LightGBM nhanh hơn XGBoost, histogram-based splitting.

**Files**:
- `[NEW] services/models/lightgbm_models.py` — LGBMReturnModel, LGBMTrendModel
- Tương tự XGBoost nhưng params khác (num_leaves, min_child_samples)
- lightgbm đã có trong requirements.txt

### 3.3 True Ensemble

**Hiện trạng**: Ensemble chỉ chứa 1 XGBoost model (weight=1.0)

**Cải thiện**: Thêm 3+ models vào ensemble:

```python
ensemble_return = EnsembleReturnModel(horizon="7d")
ensemble_return.add_model(xgb_return, weight=0.35)
ensemble_return.add_model(lgbm_return, weight=0.30)
ensemble_return.add_model(lstm_return, weight=0.35)
```

**Dynamic weights** (tương lai): Dựa trên recent window performance để auto-adjust weights.

**Files**:
- `services/models/model_trainer.py` — Tích hợp LSTM + LightGBM vào pipeline
- `services/models/ensemble_model.py` — Sửa sang EnsembleReturnModel

### Files thay đổi Phase 3

| File | Hành động | Mô tả |
|------|-----------|-------|
| `[NEW] services/models/lstm_models.py` | NEW | LSTM/GRU return + trend (override save/load) |
| `[NEW] services/models/lightgbm_models.py` | NEW | LightGBM return + trend |
| `[NEW] services/models/sequence_builder.py` | NEW | Sliding window builder cho LSTM |
| `services/models/model_trainer.py` | MODIFY | Tích hợp 3 model types |
| `services/models/ensemble_model.py` | MODIFY | True multi-model ensemble |
| `services/models/base_model.py` | MODIFY | Hỗ trợ Keras save/load (hoặc hook method) |

---

# PHASE 4: Backtesting Framework

> **Mục tiêu**: Đo lường profitability thực tế của strategy
> **Effort ước lượng**: 6-8 giờ
> **Impact**: 🔴 Cao — Biết strategy có profitable không

### 4.1 Backtesting Engine

```python
class Backtester:
    """
    Walk-forward backtest trên giá vàng lịch sử.
    
    Strategy: Theo signal của model
    - predicted_trend = TĂNG → BUY
    - predicted_trend = GIẢM → SELL/HOLD
    - predicted_trend = SIDEWAY → HOLD
    """
    
    def backtest(self, df, model, initial_capital=100_000):
        # Walk-forward: train → predict → execute → move window
        # Return: equity_curve, trades, metrics
```

**Metrics**:
- Total return, Annualized return
- Sharpe ratio, Sortino ratio
- Max drawdown, Calmar ratio
- Win rate, Profit factor
- Number of trades, Average holding period

### 4.2 Position Sizing (Kelly Criterion)

```python
# Kelly fraction = (bp - q) / b
# b = odds (win_amount / loss_amount)
# p = probability of winning
# q = 1 - p
kelly_fraction = (win_pct * avg_win / avg_loss - (1 - win_pct)) / (avg_win / avg_loss)
```

### 4.3 Risk Metrics

- **Value at Risk (VaR)**: Mức lỗ tối đa ở confidence level 95%
- **Expected Shortfall (CVaR)**: Mức lỗ trung bình khi vượt VaR
- **Stop-loss levels**: Based on ATR

### Files thay đổi Phase 4

| File | Hành động | Mô tả |
|------|-----------|-------|
| `[NEW] services/backtesting/backtester.py` | NEW | Core backtest engine |
| `[NEW] services/backtesting/risk_metrics.py` | NEW | VaR, Sharpe, Kelly |
| `[NEW] services/backtesting/report_generator.py` | NEW | Generate HTML/JSON report |
| `api/routes/gold_routes.py` | MODIFY | Endpoint GET /api/v1/backtest |

---

# PHASE 5: API & Frontend Updates

> **Mục tiêu**: Hiển thị tất cả data mới trên dashboard
> **Effort ước lượng**: 6-8 giờ
> **Impact**: 🟡 Trung bình — UX improvement

### 5.1 API Endpoints mới

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| GET | `/api/v1/backtest` | Chạy backtest + return equity curve |
| GET | `/api/v1/backtest/metrics` | Sharpe, MaxDD, Win rate... |
| GET | `/api/v1/models/compare` | So sánh accuracy XGBoost vs LSTM vs LightGBM |
| GET | `/api/v1/fear-greed` | Fear & Greed Index hiện tại |
| GET | `/api/v1/sentiment` | Sentiment tin tức hôm nay |

### 5.2 Frontend Dashboard Updates

- **Model Comparison Panel**: Bảng so sánh accuracy 3 models theo horizon
- **Backtest Equity Curve**: Line chart equity curve (Recharts)
- **Sentiment Gauge**: Fear & Greed index dạng gauge meter
- **News Sentiment**: List tin tức + sentiment score color-coded
- **Risk Dashboard**: VaR, Sharpe ratio, Max drawdown cards

### Files thay đổi Phase 5

| File | Hành động | Mô tả |
|------|-----------|-------|
| `api/routes/gold_routes.py` | MODIFY | Thêm 5 endpoints mới |
| `frontend/src/api.js` | MODIFY | Thêm API functions |
| `frontend/src/App.jsx` | MODIFY | Thêm panels mới |
| `frontend/src/index.css` | MODIFY | CSS cho panels mới |

---

# PHASE 6: Testing & Documentation

> **Mục tiêu**: Đảm bảo chất lượng code và dễ maintain
> **Effort ước lượng**: 4-6 giờ
> **Impact**: 🟡 Trung bình — Long term quality

### 6.1 Unit Tests

- `tests/test_feature_builder.py` — Test feature output shape, NaN handling
- `tests/test_model_trainer.py` — Test walk-forward, return prediction
- `tests/test_backtester.py` — Test backtest engine, metrics calculation
- `tests/test_collectors.py` — Test data collection + validation

### 6.2 Integration Tests

- Test full pipeline: collect → features → train → predict → backtest
- Test API endpoints return correct format

### 6.3 Cập nhật Documentation

- `.agent/docs/architecture-overview.md` — Cập nhật kiến trúc mới
- `.agent/skills/vn-gold-prediction/SKILL.md` — Update với LSTM
- `README.md` — Hướng dẫn setup + run

---

## Rủi ro / Edge cases

| Risk | Mức độ | Giải pháp |
|------|--------|-----------|
| LSTM train quá chậm trên CPU | 🟡 Trung bình | Giảm epochs/sequence_length, dùng GPU nếu có |
| **LSTM save/load incompatible** với joblib | 🔴 Cao | Override save/load trong LSTMReturnModel dùng Keras native |
| FRED API cần key riêng | 🟢 Thấp | Free key, đăng ký tại fred.stlouisfed.org |
| Sentiment analysis không chính xác cho tiếng Việt | 🟡 Trung bình | Dùng Gemini API thay FinBERT |
| Walk-forward chạy rất lâu (train nhiều lần) | 🟡 Trung bình | Cache models, giảm n_estimators khi tuning |
| Data leakage vẫn còn sau fix | 🔴 Cao | Kiểm tra bằng shuffled test: nếu accuracy giảm → good |
| **Trend threshold không hợp lý** cho horizon dài | 🟡 Trung bình | Dynamic threshold: 0.5% (1d), 1% (7d), 2% (30d) |

---

## Lộ trình triển khai

```
Phase 1 (ML Fix)        ████████████░░░░░░░░░░░░░░░░░░░░  Week 1
Phase 2 (Data Sources)   ░░░░░░░░░░░░████████████░░░░░░░░  Week 2
Phase 3 (Deep Learning)  ░░░░░░░░░░░░░░░░░░░░░░░█████████  Week 3
Phase 4 (Backtesting)    ░░░░░░░░░░░░░░░░░░░░░░░░░░██████  Week 3-4
Phase 5 (API + Frontend) ░░░░░░░░░░░░░░░░░░░░░░░░░░░░████  Week 4
Phase 6 (Testing + Docs) ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░██  Week 4
```

**Tổng effort ước lượng: 40-50 giờ (3-4 tuần nếu làm part-time)**

---

## Test Plan

### Automated Tests

**Phase 1 verification:**
```bash
# Chạy walk-forward validation, so sánh metrics cũ vs mới
cd backend
python -m pytest tests/test_model_trainer.py -v

# Verify return prediction: predicted_price phải hợp lý (không còn dự đoán $2,957)
python -c "
from app.services.models.model_trainer import ModelTrainer
t = ModelTrainer()
t.train_all('7d')
r = t.predict('7d')
print(f'Predicted: ${r[\"predicted_price\"]:,.2f}')
assert 3000 < r['predicted_price'] < 6000, 'Price out of range!'
"
```

**Phase 3 verification:**
```bash
# So sánh 3 models
python -c "
from app.services.models.model_trainer import ModelTrainer
t = ModelTrainer()
results = t.walk_forward_validate('7d')
print('Walk-forward results:')
for model, metrics in results.items():
    print(f'  {model}: MAE={metrics[\"avg_mae\"]:.2f}, Accuracy={metrics[\"avg_accuracy\"]:.2%}')
"
```

**Phase 4 verification:**
```bash
# Chạy backtest
python -c "
from app.services.backtesting.backtester import Backtester
bt = Backtester()
results = bt.backtest(initial_capital=100000)
print(f'Sharpe: {results[\"sharpe\"]:.2f}, MaxDD: {results[\"max_drawdown\"]:.1%}')
"
```

### Manual Verification

1. **Mở dashboard** `http://localhost:5173` → verify tất cả panels mới hiển thị
2. **Bấm "Chạy dự đoán"** → verify giá dự đoán hợp lý (không còn $2,957)
3. **Kiểm tra GET `/api/v1/models/compare`** → verify 3 models so sánh
4. **Kiểm tra GET `/api/v1/backtest/metrics`** → verify Sharpe, MaxDD

---

## Những điểm dễ thay đổi trong tương lai

| Điểm | Cách thay đổi |
|------|--------------|
| Thêm model mới (Transformer, CNN) | Implement BaseModel interface → thêm vào ensemble |
| Thêm data source mới | Implement BaseCollector → thêm vào DataPipeline |
| Thay đổi backtest strategy | Tạo class kế thừa BaseStrategy |
| Thêm horizon mới (3d, 14d) | Thêm vào `PREDICTION_HORIZONS` trong constants.py |
| Đổi sentiment model | Swap module trong `sentiment_analyzer.py` |

## Nơi nên tách module/hàm

| Module/Hàm | Lý do tách |
|------------|-----------|
| `walk_forward_validator.py` | Logic complex, tái sử dụng cho nhiều model types |
| `sequence_builder.py` | LSTM cần sliding window, tách riêng khỏi feature_builder |
| `BaseStrategy` class | Backtesting strategy pattern để dễ swap strategies |
| `model_registry.py` | Quản lý registered models, weights, versioning |
