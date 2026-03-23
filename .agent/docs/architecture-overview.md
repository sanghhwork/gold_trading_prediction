# 🥇 Gold Predictor - Tài Liệu Kiến Trúc Ứng Dụng

> Cập nhật: 23/03/2026
> Mô tả chi tiết toàn bộ quy trình thu thập, phân tích và hiển thị dữ liệu.

---

## 📋 Mục lục

1. [Tổng quan kiến trúc](#1-tong-quan-kien-truc)
2. [Thu thập dữ liệu (Data Collection)](#2-thu-thap-du-lieu)
3. [Feature Engineering](#3-feature-engineering)
4. [ML Models & Dự đoán](#4-ml-models--du-doan)
5. [AI Reasoning & Giải thích](#5-ai-reasoning--giai-thich)
6. [Dự đoán giá vàng Việt Nam](#6-du-doan-gia-vang-viet-nam)
7. [API Layer](#7-api-layer)
8. [Frontend Dashboard](#8-frontend-dashboard)
9. [Lịch tự động (Scheduler)](#9-lich-tu-dong-scheduler)
10. [Luồng dữ liệu End-to-End](#10-luong-du-lieu-end-to-end)

---

## 1. Tổng quan kiến trúc

```
┌─────────────────────────────────────────────────────────────┐
│                      FRONTEND (React + Vite)                 │
│   Dashboard: Chart, Stats, VN Gold, SHAP, Advisor            │
│   Port: 5173 (dev) / 80 (nginx production)                   │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP REST API
┌──────────────────────▼──────────────────────────────────────┐
│                      BACKEND (FastAPI)                        │
│   Port: 8001                                                  │
│   ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌───────────────┐   │
│   │ API     │ │ Scheduler│ │ Models   │ │ AI Reasoning  │   │
│   │ Routes  │ │ (APSched)│ │ (XGBoost)│ │ (SHAP/Rules)  │   │
│   └────┬────┘ └──────────┘ └──────────┘ └───────────────┘   │
│        │                                                      │
│   ┌────▼─────────────────────────────────────────────────┐   │
│   │              DATA COLLECTORS                          │   │
│   │  XAU (yfinance) │ SJC (sjc.com.vn) │ giavang.org    │   │
│   │  Macro (yfinance)│ giavang.net       │ News (cafef)  │   │
│   └──────────────────────────────────────────────────────┘   │
│                       │                                       │
│                  ┌────▼────┐                                  │
│                  │ SQLite  │                                   │
│                  │   DB    │                                   │
│                  └─────────┘                                  │
└──────────────────────────────────────────────────────────────┘
```

### Cấu trúc thư mục backend

```
backend/app/
├── main.py                        # FastAPI entry point + lifespan
├── config.py                      # Cấu hình từ .env (pydantic-settings)
├── scheduler.py                   # APScheduler (daily collect, weekly retrain)
├── api/
│   ├── routes/gold_routes.py      # 14 API endpoints
│   └── schemas/gold_schemas.py    # Pydantic response models
├── db/
│   ├── database.py                # SQLAlchemy engine + session
│   └── models.py                  # GoldPrice, MacroIndicator, Prediction...
├── services/
│   ├── data_collector/
│   │   ├── base_collector.py      # Abstract base class
│   │   ├── data_pipeline.py       # Orchestrator chạy tất cả collectors
│   │   ├── xau_collector.py       # XAU/USD từ Yahoo Finance
│   │   ├── sjc_collector.py       # SJC từ sjc.com.vn + giavang.net
│   │   ├── giavang_org_collector.py # SJC/PNJ/DOJI từ giavang.org
│   │   ├── macro_collector.py     # DXY, Oil, US10Y, SP500, USD/VND
│   │   └── news_collector.py      # Tin tức từ cafef.vn
│   ├── feature_engine/
│   │   ├── feature_builder.py     # Build 92 features từ raw data
│   │   ├── technical_indicators.py # RSI, MACD, BB, SMA, ATR...
│   │   └── macro_features.py      # Cross-features giữa gold & macro
│   ├── models/
│   │   ├── model_trainer.py       # Train + predict orchestrator
│   │   ├── xgboost_models.py      # XGBoost price + trend models
│   │   ├── ensemble_model.py      # Ensemble (XGBoost weighted avg)
│   │   ├── vn_gold_predictor.py   # XAU → SJC VND conversion
│   │   └── base_model.py          # Abstract base class
│   ├── ai_reasoning/
│   │   ├── market_analyzer.py     # Rule-based technical analysis
│   │   ├── prediction_explainer.py # SHAP values explanation
│   │   └── gemini_client.py       # Google Gemini AI (khi có key)
│   └── advisor/
│       └── investment_advisor.py  # Buy/Sell/Hold recommendation
└── utils/
    ├── constants.py               # PREDICTION_HORIZONS, TREND_LABELS
    └── logger.py                  # Loguru logging config
```

---

## 2. Thu thập dữ liệu (Data Collection)

### 2.1 Tổng quan các nguồn

| # | Collector | Nguồn | Dữ liệu | Phương thức | Records |
|---|-----------|-------|----------|-------------|---------|
| 1 | `XAUCollector` | Yahoo Finance (`GC=F`) | XAU/USD OHLCV | API (yfinance) | ~1257 |
| 2 | `SJCCollector` | sjc.com.vn + giavang.net | SJC buy/sell | POST API + GET API | ~1/ngày |
| 3 | `GiavangOrgCollector` | giavang.org | SJC/PNJ/DOJI/nhiều đơn vị | HTML scraping | ~35/ngày |
| 4 | `MacroCollector` | Yahoo Finance | DXY, Oil, US10Y, SP500, USD/VND | API (yfinance) | ~1300 |
| 5 | `NewsCollector` | cafef.vn | Tin tức giá vàng | HTML scraping | Tùy ngày |

### 2.2 Chi tiết từng Collector

#### 📊 XAU Collector (`xau_collector.py`)
```
Nguồn:     Yahoo Finance - ticker "GC=F"
Dữ liệu:  Open, High, Low, Close, Volume (USD/oz)
Lịch sử:  5 năm gần nhất (~1257 trading days)
Tần suất:  1 lần/ngày (scheduler 8:00 AM)
Lưu vào:   bảng gold_prices (source="xau_usd")
```

#### 🇻🇳 SJC Collector (`sjc_collector.py`)
```
Nguồn 1 (Primary):  POST https://sjc.com.vn/GoldPrice/Services/PriceService.ashx
                     Body: method=GetCurrentGoldPricesByBranch&BranchId=1
                     → JSON response: { BuyValue, SellValue, TypeName }

Nguồn 2 (Fallback): GET https://api2.giavang.net/v1/gold/last-price?codes[]=SJL1L10
                     → JSON response: { buy, sell }

Dữ liệu:  SJC 1L,10L,1KG - Mua (VND), Bán (VND)
Tần suất:  1 lần/ngày (scheduler 8:00 AM)
Lưu vào:   bảng gold_prices (source="sjc")
```

#### 🏢 Giavang.org Collector (`giavang_org_collector.py`)
```
Nguồn realtime: https://giavang.org/
                 → HTML table: Khu vực | Hệ thống | Mua vào | Bán ra
                 → Parse BeautifulSoup

Nguồn lịch sử:  https://giavang.org/trong-nuoc/sjc/lich-su/YYYY-MM-DD.html
                 → Crawl từng ngày (có từ 07/2009)

Dữ liệu:  Nhiều đơn vị (SJC, PNJ, DOJI, Mi Hồng, Ngọc Thẩm)
           Nhiều khu vực (HCM, HN, Đà Nẵng, Hạ Long...)
           Đơn vị: x1000 VND/lượng (163.000 = 163,000,000 VND)
Tần suất:  1 lần/ngày (scheduler)
Lưu vào:   bảng gold_prices (source="giavang_org", chỉ SJC chính)
```

#### 📈 Macro Collector (`macro_collector.py`)
```
Nguồn:     Yahoo Finance
Tickers:   DX-Y.NYB (DXY), CL=F (Oil WTI), ^TNX (US 10Y),
           ^GSPC (S&P500), VND=X (USD/VND)
Dữ liệu:  Close price, % change
Lịch sử:  5 năm (~1300 records mỗi indicator)
Lưu vào:   bảng macro_indicators (indicator="dxy"|"oil_wti"|...)
```

### 2.3 Luồng thu thập (Data Pipeline)

```
DataPipeline.run_all()
    │
    ├── 1. XAUCollector.collect_and_store()
    │      fetch_data() → validate_data() → store_data()
    │
    ├── 2. SJCCollector.collect_and_store()
    │      _fetch_sjc_api() → fallback _fetch_giavang_net() → validate → store
    │
    ├── 3. GiavangOrgCollector.collect_and_store()
    │      _fetch_today() → _parse_price_table() → validate → store (SJC only)
    │
    ├── 4. MacroCollector.collect_and_store()
    │      fetch 5 tickers → validate → store
    │
    └── 5. NewsCollector.collect_and_store()
           scrape cafef.vn → parse articles → store
```

### 2.4 Database Schema

```sql
gold_prices:
  id, date, source, open, high, low, close, volume,
  buy_price, sell_price, created_at, updated_at

macro_indicators:
  id, date, indicator, open, high, low, close, volume,
  created_at, updated_at

predictions:
  id, date, horizon, predicted_price, predicted_trend,
  trend_probabilities, model_name, created_at

news_articles:
  id, title, url, source, content, sentiment, published_at

ai_analyses:
  id, date, analysis_text, ai_provider, created_at
```

---

## 3. Feature Engineering

### 3.1 Tổng: 92 features

```
FeatureBuilder.build_features(source="xau_usd", include_macro=True)
    │
    ├── Technical Indicators (~30 features)
    │   ├── SMA 5, 10, 20, 50, 100, 200
    │   ├── EMA 12, 26
    │   ├── RSI (14), Stochastic %K
    │   ├── MACD, MACD Signal, MACD Histogram
    │   ├── Bollinger Bands (upper, lower, width, position)
    │   ├── ATR (14), ATR %
    │   ├── Williams %R
    │   └── SMA crossovers (golden/death cross)
    │
    ├── Price Features (~20 features)
    │   ├── Returns: 1d, 2d, 5d, 10d, 20d, 60d
    │   ├── Volatility: 5d, 10d, 20d
    │   ├── Price vs SMA ratios
    │   └── High-Low range, Body size
    │
    ├── Macro Cross-Features (~30 features)
    │   ├── DXY: value, change 1d/5d, RSI, SMA20, ratio với gold
    │   ├── Oil WTI: value, change 1d/5d, ratio với gold
    │   ├── US 10Y: value, change 1d/5d
    │   ├── S&P 500: value, change 1d/5d
    │   ├── USD/VND: value, change 1d/5d
    │   └── Gold-DXY ratio, Gold-Oil ratio + changes
    │
    ├── Calendar (~5 features)
    │   ├── day_of_week, month, quarter
    │   └── is_month_start, is_month_end
    │
    └── Target Variables (3 horizons)
        ├── target_return_1d/7d/30d  (% change)
        └── target_trend_1d/7d/30d   (0=Giảm, 1=Sideway, 2=Tăng)
```

### 3.2 Cách tính Target

```python
# Trend classification:
- Giảm (0):   return < -1%
- Sideway (1): -1% ≤ return ≤ +1%
- Tăng (2):   return > +1%
```

---

## 4. ML Models & Dự đoán

### 4.1 Kiến trúc Models

```
ModelTrainer
    │
    ├── train_all(horizon="7d")
    │   ├── XGBoost Price Model → Dự đoán giá tuyệt đối (regression)
    │   ├── XGBoost Trend Model → Dự đoán xu hướng (classification 3 classes)
    │   ├── Ensemble Price Model → Weighted average of models
    │   └── Ensemble Trend Model → Weighted average of models
    │
    └── predict(horizon="7d")
        → { predicted_price, confidence_lower, confidence_upper,
             predicted_trend, trend_probabilities }
```

### 4.2 Chi tiết Models

| Model | Loại | Output | Metrics |
|-------|------|--------|---------|
| XGBoost Price | Regression | Giá USD/oz | MAE, RMSE, R² |
| XGBoost Trend | Classification | 0/1/2 (Giảm/Sideway/Tăng) | Accuracy, F1, Precision |
| Ensemble Price | Weighted Avg | Giá trung bình + confidence | MAE, RMSE |
| Ensemble Trend | Weighted Avg | Xác suất 3 classes | Accuracy |

### 4.3 Horizons (Khoảng thời gian dự đoán)

| Horizon | Ý nghĩa | Accuracy (trend) |
|---------|---------|-------------------|
| **1d** | Ngày mai | ~50-55% |
| **7d** | 1 tuần tới | ~55-60% |
| **30d** | 1 tháng tới | ~60-66% |

### 4.4 Saved Models

```
backend/saved_models/
├── xgboost_price_1d.joblib
├── xgboost_price_7d.joblib
├── xgboost_price_30d.joblib
├── xgboost_trend_1d.joblib
├── xgboost_trend_7d.joblib
├── xgboost_trend_30d.joblib
├── ensemble_price_1d.joblib
├── ensemble_price_7d.joblib
├── ensemble_price_30d.joblib
├── ensemble_trend_1d.joblib
├── ensemble_trend_7d.joblib
└── ensemble_trend_30d.joblib
```

---

## 5. AI Reasoning & Giải thích

### 5.1 Rule-based Market Analyzer (`market_analyzer.py`)

```
Phân tích dựa trên điểm số (scoring system):

RSI:
  < 30 → STRONG BUY (+2), 30-40 → BUY (+1)
  > 70 → STRONG SELL (-2), 60-70 → SELL (-1)

MACD:
  Histogram > 0 && tăng → BUY (+1)
  Histogram < 0 && giảm → SELL (-1)

Bollinger Bands:
  Position < 0.2 → BUY (+1, gần lower band)
  Position > 0.8 → SELL (-1, gần upper band)

SMA Crossover:
  SMA50 > SMA200 → Golden Cross → BUY (+1)
  SMA50 < SMA200 → Death Cross → SELL (-1)

Tổng điểm → Recommendation: STRONG BUY / BUY / HOLD / SELL / STRONG SELL
```

### 5.2 SHAP Prediction Explainer (`prediction_explainer.py`)

```
Input:  Trained XGBoost model + latest features
Output: Top 8 yếu tố ảnh hưởng nhất
        Mỗi yếu tố: { feature, display_name, shap_value, direction, context }

Ví dụ output:
  📈 Đẩy TĂNG:
    + Giá dầu WTI = 85.2 (Dầu tăng → lạm phát → vàng tăng)
    + DXY RSI = 28 (USD yếu → vàng tăng)
  📉 Đẩy GIẢM:
    - Lãi suất US 10Y = 4.5% (chi phí cơ hội giữ vàng tăng)
    - S&P 500 = +1.2% (risk appetite cao → giảm safe-haven demand)
```

### 5.3 Investment Advisor (`investment_advisor.py`)

```
Input:  Predictions + Technical Analysis + Market Analyzer
Output: {
  recommendation: "BUY" / "SELL" / "HOLD",
  confidence: 0.0 - 1.0,
  risk_level: "LOW" / "MEDIUM" / "HIGH" / "VERY_HIGH",
  summary: "Lời khuyên chi tiết...",
  technical_snapshot: { rsi, macd, bb_position, atr_pct, ... }
}
```

---

## 6. Dự đoán giá vàng Việt Nam

### 6.1 Công thức quy đổi (`vn_gold_predictor.py`)

```
SJC (VND/lượng) = XAU/USD × USD/VND × (37.5 / 31.1035) + Premium

Trong đó:
  37.5g     = 1 lượng vàng Việt Nam
  31.1035g  = 1 troy ounce (đơn vị quốc tế)
  1.2057    = 37.5 / 31.1035 (hệ số quy đổi)
  Premium   = Chênh lệch SJC so với thế giới (thường 5-20 triệu VND)
```

### 6.2 Luồng dự đoán SJC

```
XGBoost predict XAU/USD (7d)
         │
         ▼
VNGoldPredictor.predict_sjc_price()
  ├── Lấy USD/VND từ DB (hoặc default 25,800)
  ├── Tính giá thế giới quy đổi = XAU × USD/VND × 1.2057
  ├── Ước lượng premium (từ SJC thực tế - giá quy đổi)
  └── SJC dự kiến = Giá quy đổi + Premium
         │
         ▼
Output: { sjc_buy, sjc_sell, premium, formula }
```

### 6.3 Nguồn so sánh giá VN (3 nguồn)

| Nguồn | Primary/Fallback | Dữ liệu | API Type |
|-------|-----------------|----------|----------|
| sjc.com.vn | Primary cho SJC | SJC chính thức | POST JSON |
| giavang.net | Fallback cho SJC | SJC tổng hợp | GET JSON |
| giavang.org | So sánh đa đơn vị | SJC, PNJ, DOJI, Mi Hồng... | HTML parse |

---

## 7. API Layer

### 7.1 Danh sách Endpoints (14 endpoints)

| Method | Endpoint | Mô tả |
|--------|----------|--------|
| GET | `/health` | Health check + scheduler status |
| GET | `/api/v1/gold/prices` | Lấy giá vàng N ngày (params: source, days) |
| GET | `/api/v1/gold/latest` | Giá vàng mới nhất |
| GET | `/api/v1/gold/summary` | Tổng quan dữ liệu trong DB |
| GET | `/api/v1/predictions/{horizon}` | Dự đoán 1 horizon (1d/7d/30d) |
| GET | `/api/v1/predictions` | Dự đoán tất cả horizons |
| GET | `/api/v1/predictions/{horizon}/explain` | SHAP giải thích dự đoán |
| GET | `/api/v1/analysis` | Phân tích thị trường (Rule-based) |
| GET | `/api/v1/advisor` | Lời khuyên đầu tư |
| GET | `/api/v1/gold/vn` | Phân tích giá vàng VN (SJC vs quy đổi) |
| GET | `/api/v1/gold/vn/predict` | Dự đoán giá SJC |
| GET | `/api/v1/gold/vn/compare` | So sánh giá nhiều đơn vị (giavang.org) |
| POST | `/api/v1/train` | Train/retrain ML models |
| POST | `/api/v1/collect-data` | Thu thập dữ liệu mới |

---

## 8. Frontend Dashboard

### 8.1 Các panels hiển thị

```
┌────────────────────────────────────────────────┐
│ 🥇 Gold Predictor                   ● Online   │
├────────┬────────┬──────────┬──────────────────┤
│XAU/USD │ SJC   │Premium   │ DB Records       │
│$4,574  │ 171M  │ 19.6%    │ 1,257            │
├────────┴────────┴──────────┴──────────────────┤
│                                                │
│ 📈 Biểu đồ XAU/USD (1 năm)     🔮 Dự đoán   │
│ [AreaChart with gold gradient]  [1d/7d/30d]   │
│                                 [Trend probs] │
├────────────────────────────────────────────────┤
│ 🇻🇳 Vàng Việt Nam (SJC)                        │
│ ┌─────────────────┐ ┌──────────────────────┐  │
│ │Premium Analysis │ │ Dự đoán SJC          │  │
│ │ TG quy đổi:143M │ │ 7d: Mua 117M/Bán 120M│  │
│ │ SJC thực: 171M  │ │ Công thức quy đổi    │  │
│ │ Premium: 28M    │ │                      │  │
│ └─────────────────┘ └──────────────────────┘  │
├────────────────────────────────────────────────┤
│ 🧠 SHAP Explanation (nếu có)                   │
│ [Bar chart: feature contributions]             │
│ [Driver cards: tên + context + direction]      │
├────────────────────────────────────────────────┤
│ 💡 Lời khuyên ĐT     │ 📊 Chỉ báo kỹ thuật   │
│ BUY/SELL/HOLD         │ RSI, MACD, BB, ATR     │
│ Confidence bar        │ SMA crossover          │
│ Summary text          │ Williams %R            │
├────────────────────────────────────────────────┤
│ 🔍 Phân tích thị trường (Rule-based/Gemini)   │
└────────────────────────────────────────────────┘
```

### 8.2 Tech stack Frontend

| Thành phần | Công nghệ |
|------------|-----------|
| Framework | React 18 + Vite |
| Charts | Recharts (AreaChart, BarChart) |
| Styling | Vanilla CSS (dark theme, glassmorphism) |
| API calls | fetch() → `api.js` wrapper functions |
| Dev server | Vite HMR - port 5173 |
| Production | Nginx (multi-stage Docker build) |

---

## 9. Lịch tự động (Scheduler)

### 9.1 Cấu hình (`scheduler.py` + `.env`)

| Job | Thời gian | Công việc | Config (.env) |
|-----|-----------|-----------|---------------|
| **Daily Collect** | 08:00 AM mỗi ngày | `DataPipeline.run_all()` | `daily_collect_time=08:00` |
| **Weekly Retrain** | 09:00 AM thứ Hai | `ModelTrainer.train_all_horizons()` | `weekly_retrain_day=0` |

### 9.2 Luồng hoạt động

```
Backend Start (uvicorn)
    │
    ├── lifespan() → init_db() → start_scheduler()
    │
    ├── ⏰ 08:00 AM hàng ngày:
    │   └── _job_collect_data()
    │       └── DataPipeline.run_all()
    │           ├── XAU: Yahoo Finance → DB
    │           ├── SJC: sjc.com.vn → DB
    │           ├── GiavangOrg: giavang.org → DB
    │           ├── Macro: Yahoo Finance → DB
    │           └── News: cafef.vn → DB
    │
    └── ⏰ 09:00 AM thứ Hai:
        └── _job_retrain_models()
            └── ModelTrainer.train_all_horizons()
                → Train XGBoost + Ensemble cho 1d/7d/30d
                → Save models → saved_models/*.joblib
```

### 9.3 Giám sát Scheduler

```
GET /health
→ {
    "status": "healthy",
    "scheduler": {
      "running": true,
      "jobs": [
        { "name": "Daily Data Collection", "next_run": "2026-03-24 08:00" },
        { "name": "Weekly Model Retrain",  "next_run": "2026-03-24 09:00" }
      ]
    }
  }
```

---

## 10. Luồng dữ liệu End-to-End

### 10.1 Khi người dùng mở Dashboard

```
User mở http://localhost:5173
    │
    ├── React gọi song song:
    │   ├── GET /gold/prices?source=xau_usd&days=365 → Chart data
    │   ├── GET /gold/latest?source=xau_usd          → XAU stat
    │   ├── GET /gold/summary                         → DB counts
    │   └── GET /gold/vn                              → SJC + Premium
    │
    └── Hiển thị: Stats + Chart + VN Gold panel
```

### 10.2 Khi bấm "Chạy dự đoán"

```
User bấm "Chạy dự đoán"
    │
    ├── React gọi song song:
    │   ├── GET /predictions           → Train all horizons → Predictions
    │   ├── GET /advisor?horizon=7d    → Rule-based analysis → Advice
    │   ├── GET /gold/vn/predict       → XAU predict → SJC conversion
    │   └── GET /predictions/7d/explain → SHAP values
    │
    ├── Backend tự động:
    │   ├── FeatureBuilder.build_features() → 92 features
    │   ├── ModelTrainer.train_all() → XGBoost + Ensemble
    │   ├── ModelTrainer.predict() → {price, trend, probabilities}
    │   ├── VNGoldPredictor.predict_sjc_price() → SJC VND
    │   ├── PredictionExplainer → SHAP drivers
    │   └── InvestmentAdvisor → Buy/Sell/Hold + Technical snapshot
    │
    └── Hiển thị: Predictions + VN Predict + SHAP chart + Advisor + Technicals
```

### 10.3 Thu thập tự động (08:00 AM hàng ngày)

```
Scheduler trigger 08:00 AM
    │
    └── DataPipeline.run_all()
        ├── XAU: yfinance.download("GC=F") → 1 new record
        ├── SJC: POST sjc.com.vn API → 1 record (buy/sell)
        │   └── Fallback: GET giavang.net API
        ├── GiavangOrg: GET giavang.org → parse HTML → 1 SJC record
        ├── Macro: yfinance.download(5 tickers) → 5 records
        └── News: scrape cafef.vn → N articles
```

---

> 📌 **Lưu ý**: Model dự đoán hiện tại được train trên dữ liệu XAU/USD (1257 records). Giá SJC Việt Nam được **tính toán** từ XAU/USD forecast qua công thức quy đổi, chưa có ML model riêng cho SJC do thiếu dữ liệu lịch sử SJC. Khi tích lũy đủ dữ liệu SJC (3-6 tháng), có thể train model riêng cho premium prediction.
