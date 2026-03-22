# 🥇 Gold Prediction - Master Plan
# Hệ thống dự đoán giá vàng thế giới (XAU/USD) & Việt Nam (SJC)

---

## 🎯 Tổng quan

Dự án tập trung **100% vào giá vàng**, tách biệt khỏi cổ phiếu (sẽ là project riêng sau).

| Mục tiêu | Chi tiết |
|-----------|----------|
| 📈 **Price Regression** | Dự đoán giá XAU/USD và SJC (1 ngày, 1 tuần, 1 tháng) |
| 🔀 **Trend Classification** | Tăng / Giảm / Sideway với xác suất % |
| 🌊 **Volatility Analysis** | Mức biến động + risk level |
| 🤖 **AI Reasoning** | Phân tích thị trường bằng Gemini AI, giải thích WHY |
| 💡 **Investment Advice** | Lời khuyên đầu tư + giải thích bằng ngôn ngữ tự nhiên |

---

## 📡 Nguồn dữ liệu

### Dữ liệu giá vàng

| Nguồn | Dữ liệu | Thư viện | Cập nhật |
|-------|----------|----------|----------|
| **yfinance** | XAU/USD (ticker: `GC=F`) | `yfinance` | Realtime (delay 15p) |
| **SJC Website** | Giá vàng SJC mua/bán | `requests` + `BeautifulSoup` | Scrape mỗi giờ |

### Dữ liệu macro (ảnh hưởng giá vàng)

| Nguồn | Dữ liệu | Vai trò | Ticker yfinance |
|-------|----------|---------|-----------------|
| **DXY** | Dollar Index | Tương quan nghịch với vàng | `DX-Y.NYB` |
| **USD/VND** | Tỷ giá | Ảnh hưởng giá vàng VN | `VND=X` |
| **Oil (WTI)** | Giá dầu | Indicator lạm phát | `CL=F` |
| **US 10Y Treasury** | Lãi suất trái phiếu Mỹ | Opportunity cost of gold | `^TNX` |
| **S&P 500** | Chỉ số thị trường Mỹ | Risk appetite indicator | `^GSPC` |
| **VN-Index** | Chỉ số VN | Tâm lý thị trường VN | N/A (dùng vnstock) |
| **US CPI** | Chỉ số lạm phát | Key driver giá vàng | FRED API hoặc manual |

### Dữ liệu tin tức (cho AI Sentiment)

| Nguồn | Mục đích |
|-------|----------|
| **cafef.vn** | Tin tức vàng VN |
| **kitco.com** | Tin tức vàng quốc tế |
| **Google News API** | Gold market news |

---

## 🏗️ Kiến trúc hệ thống

```
┌──────────────────────────────────────────────────────────────────────────┐
│                     Gold Prediction System                               │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─── Data Layer ───┐  ┌── Feature Eng. ──┐  ┌──── ML Models ────┐     │
│  │                   │  │                  │  │                    │     │
│  │ • XAU/USD (yf)    │→ │ • Technical      │→ │ • XGBoost (Price) │     │
│  │ • SJC (scraping)  │  │   Indicators     │  │ • LSTM (Price)    │     │
│  │ • DXY, Oil, Rates │  │ • Macro Features │  │ • Prophet (Trend) │     │
│  │ • USD/VND         │  │ • Calendar/Lag   │  │ • GARCH (Vol)     │     │
│  │ • News/Sentiment  │  │ • Correlations   │  │ • Ensemble        │     │
│  └───────────────────┘  └──────────────────┘  └────────┬─────────┘     │
│                                                         │               │
│  ┌─── AI Reasoning Layer (Gemini API) ──────────────────┤               │
│  │                                                      │               │
│  │ • News Sentiment Analysis ────────────────────┐      │               │
│  │ • Market Context Reasoning ───────────────┐   │      │               │
│  │ • Pattern Interpretation ─────────────┐   │   │      │               │
│  │                                       ▼   ▼   ▼      │               │
│  │                              ┌────────────────────┐  │               │
│  │                              │  AI Analysis       │  │               │
│  │                              │  Engine             │  │               │
│  │                              └─────────┬──────────┘  │               │
│  └────────────────────────────────────────┼─────────────┘               │
│                                           │                             │
│                              ┌────────────▼────────────┐                │
│                              │   Investment Advisor    │                │
│                              │                         │                │
│                              │ ML Predictions ──┐      │                │
│                              │ AI Reasoning ────┤──► Advice             │
│                              │ Risk Assessment ─┘      │                │
│                              └────────────┬────────────┘                │
│                                           │                             │
│                              ┌────────────▼────────────┐                │
│                              │    FastAPI + WebSocket   │                │
│                              └────────────┬────────────┘                │
│                                           │                             │
│                              ┌────────────▼────────────┐                │
│                              │   React Web Dashboard   │                │
│                              └─────────────────────────┘                │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Tech Stack

| Layer | Công cụ | Ghi chú |
|-------|---------|---------|
| **Language** | Python 3.11+ | Backend + ML |
| **API** | FastAPI + Uvicorn | REST + WebSocket |
| **Database** | SQLite (dev) → PostgreSQL (prod) | Lưu dữ liệu lịch sử |
| **ML** | scikit-learn, XGBoost, TensorFlow/Keras | Prediction models |
| **Time-series** | Prophet, arch (GARCH) | Specialized models |
| **AI Reasoning** | Google Gemini API (`google-generativeai`) | Phân tích + tư vấn |
| **Data** | pandas, numpy, yfinance, vnstock, ta | Thu thập + xử lý |
| **Frontend** | React (Vite) + Recharts + Ant Design | Dashboard |
| **Scheduler** | APScheduler | Auto data collection |

---

## 📁 Cấu trúc dự án

```
FinanceTrading/
├── .agent/
│   ├── docs/                              # Tài liệu kỹ thuật
│   ├── plans/                             # Kế hoạch triển khai
│   ├── workflows/                         # 🔧 Antigravity workflows
│   │   ├── collect-gold-data.md           # Workflow thu thập dữ liệu
│   │   ├── train-gold-models.md           # Workflow train models
│   │   ├── run-prediction.md              # Workflow chạy prediction
│   │   └── backtest-strategy.md           # Workflow backtesting
│   └── skills/                            # 🧠 Antigravity skills
│       ├── gold-data-pipeline/            
│       │   └── SKILL.md                   
│       ├── feature-engineering/           
│       │   └── SKILL.md                   
│       ├── model-training/                
│       │   └── SKILL.md                   
│       ├── ai-market-analysis/            
│       │   └── SKILL.md                   
│       └── backtesting/                   
│           └── SKILL.md                   
│
├── backend/
│   ├── app/
│   │   ├── main.py                        # FastAPI entry point
│   │   ├── config.py                      # Config & .env loading
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   ├── gold.py                # API giá vàng (XAU + SJC)
│   │   │   │   ├── predictions.py         # API dự đoán
│   │   │   │   ├── advisor.py             # API lời khuyên đầu tư
│   │   │   │   └── analysis.py            # API phân tích AI
│   │   │   └── schemas/
│   │   │       ├── gold_schemas.py
│   │   │       ├── prediction_schemas.py
│   │   │       └── advisor_schemas.py
│   │   ├── services/
│   │   │   ├── data_collector/
│   │   │   │   ├── base_collector.py      # Abstract base
│   │   │   │   ├── xau_collector.py       # XAU/USD từ yfinance
│   │   │   │   ├── sjc_collector.py       # SJC từ scraping
│   │   │   │   ├── macro_collector.py     # DXY, Oil, Rates, USD/VND
│   │   │   │   └── news_collector.py      # Tin tức vàng
│   │   │   ├── feature_engine/
│   │   │   │   ├── technical_indicators.py
│   │   │   │   ├── macro_features.py
│   │   │   │   └── feature_builder.py
│   │   │   ├── models/
│   │   │   │   ├── base_model.py
│   │   │   │   ├── price_predictor.py     # XGBoost + LSTM
│   │   │   │   ├── trend_classifier.py    # Trend prediction
│   │   │   │   ├── volatility_predictor.py # GARCH
│   │   │   │   └── ensemble.py            # Weighted ensemble
│   │   │   ├── ai_reasoning/              # 🤖 AI Reasoning Layer
│   │   │   │   ├── gemini_client.py       # Gemini API wrapper
│   │   │   │   ├── market_analyzer.py     # AI market analysis
│   │   │   │   ├── sentiment_analyzer.py  # AI news sentiment
│   │   │   │   └── insight_generator.py   # Generate explanations
│   │   │   ├── advisor/
│   │   │   │   ├── investment_advisor.py   # Combine ML + AI → Advice
│   │   │   │   └── risk_assessor.py
│   │   │   └── backtesting/
│   │   │       └── backtester.py
│   │   ├── db/
│   │   │   ├── database.py
│   │   │   └── models.py
│   │   └── utils/
│   │       ├── logger.py
│   │       └── constants.py
│   ├── requirements.txt
│   └── tests/
│
├── frontend/
│   └── (React Vite app - Phase 7)
│
├── data/                                  # Local data cache
├── saved_models/                          # Trained ML models
├── notebooks/                             # Jupyter exploration
├── .env.example
└── README.md
```

---

## 📋 Phases triển khai chi tiết

---

### Phase 1: Project Foundation ⏱️ 1 session

**Mục tiêu**: Setup project cơ bản, sẵn sàng phát triển

| # | Task | Chi tiết |
|---|------|----------|
| 1.1 | Python project setup | `venv`, `requirements.txt`, project structure |
| 1.2 | Database schema | Tables: `gold_prices`, `macro_indicators`, `predictions`, `news` |
| 1.3 | Logger & Config | Logging utility + `.env` config loading |
| 1.4 | Constants | Tickers, URLs, model params |

> 🔧 **GA Integration Point #1**: Tạo `gold-data-pipeline` skill + `/collect-gold-data` workflow

---

### Phase 2: Data Collection ⏱️ 2 sessions

**Mục tiêu**: Thu thập đầy đủ dữ liệu vàng + macro indicators

| # | Task | Chi tiết |
|---|------|----------|
| 2.1 | `xau_collector.py` | Thu thập XAU/USD OHLCV từ yfinance (5+ năm lịch sử) |
| 2.2 | `sjc_collector.py` | Scrape giá SJC (mua/bán) từ sjc.com.vn |
| 2.3 | `macro_collector.py` | DXY, USD/VND, Oil, US 10Y, S&P 500, CPI |
| 2.4 | `news_collector.py` | Thu thập headlines tin tức vàng |
| 2.5 | Data pipeline | Validate, clean, fill missing, store to DB |
| 2.6 | Scheduled collection | APScheduler auto-collect hàng ngày |

```
Luồng thu thập dữ liệu:

┌─────────────┐    ┌──────────────┐    ┌──────────────┐
│  yfinance   │    │ SJC Scraper  │    │ News Scraper │
│ XAU,DXY,Oil │    │ goldprice.vn │    │ cafef,kitco  │
└──────┬──────┘    └──────┬───────┘    └──────┬───────┘
       │                  │                   │
       └──────────────────┴───────────────────┘
                          │
                 ┌────────▼────────┐
                 │  Data Validator │  ← Kiểm tra missing, outliers
                 └────────┬────────┘
                          │
                 ┌────────▼────────┐
                 │  SQLite/PgSQL   │  ← Lưu trữ lịch sử
                 └─────────────────┘
```

> 🔧 **GA Integration Point #2**: Update `gold-data-pipeline` skill với hướng dẫn troubleshoot scraping + data quality

---

### Phase 3: Feature Engineering ⏱️ 1-2 sessions

**Mục tiêu**: Xây pipeline tạo features cho ML models

| # | Task | Feature | Mô tả |
|---|------|---------|--------|
| 3.1 | Technical Indicators | SMA(20,50,200), EMA(12,26) | Moving averages |
| 3.2 | | RSI(14), MACD(12,26,9) | Momentum indicators |
| 3.3 | | Bollinger Bands(20,2) | Volatility bands |
| 3.4 | | ATR(14), OBV | Volatility & volume |
| 3.5 | | Stochastic(14,3), Williams %R | Oscillators |
| 3.6 | Macro Features | DXY_change, Rate_change | % thay đổi macro |
| 3.7 | | Gold_DXY_ratio | Correlation features |
| 3.8 | | Oil_Gold_spread | Cross-asset spread |
| 3.9 | Calendar | day_of_week, month, quarter | Seasonal patterns |
| 3.10 | Lag Features | price_lag_1/5/10/20d | Historical lags |
| 3.11 | Return Features | return_1d, return_5d, return_20d | % returns |
| 3.12 | Feature Builder | Pipeline chạy toàn bộ | Auto-generate matrix |

> 🔧 **GA Integration Point #3**: Tạo `feature-engineering` skill - hướng dẫn cách thêm/sửa features

---

### Phase 4: ML Models ⏱️ 2-3 sessions

**Mục tiêu**: Train & đánh giá các models dự đoán giá vàng

#### 4A. Price Prediction (Regression)

| # | Model | Input | Output | Metrics |
|---|-------|-------|--------|---------|
| 4.1 | XGBoost Regressor | Feature matrix | Giá XAU ngày mai | MAE, RMSE, MAPE |
| 4.2 | LSTM/GRU | Sequence 60 ngày | Giá XAU N ngày tới | MAE, RMSE, MAPE |
| 4.3 | Prophet | Time-series | Trend + Seasonality | MAE, RMSE |

#### 4B. Trend Classification

| # | Model | Output | Metrics |
|---|-------|--------|---------|
| 4.4 | XGBoost Classifier | Tăng/Giảm/Sideway (3 class) | Accuracy, F1, AUC |
| 4.5 | LSTM Classifier | Tăng/Giảm/Sideway (3 class) | Accuracy, F1, AUC |

#### 4C. Volatility Prediction

| # | Model | Output | Metrics |
|---|-------|--------|---------|
| 4.6 | GARCH(1,1) | Volatility forecast | MSE, Log-likelihood |
| 4.7 | XGBoost on ATR features | Volatility class (High/Med/Low) | Accuracy, F1 |

#### 4D. Ensemble & Evaluation

| # | Task | Chi tiết |
|---|------|----------|
| 4.8 | Weighted Ensemble | Combine top models dựa vào recent performance |
| 4.9 | Walk-forward validation | Time-series cross-validation (không random split!) |
| 4.10 | Backtesting framework | Simulate trades, tính Sharpe, Drawdown, Win Rate |

> ⚠️ **Lưu ý**: Time-series validation PHẢI dùng walk-forward, KHÔNG ĐƯỢC random split (gây data leakage)

> 🔧 **GA Integration Point #4**: Tạo `model-training` skill + `backtesting` skill + `/train-gold-models` workflow + `/backtest-strategy` workflow

---

### Phase 5: 🤖 AI Reasoning Integration ⏱️ 1-2 sessions

> 📌 **PHASE QUAN TRỌNG - Đây là điểm khác biệt lớn nhất của hệ thống**

**Mục tiêu**: Tích hợp Gemini AI để phân tích sâu, giải thích predictions

| # | Task | Chi tiết |
|---|------|----------|
| 5.1 | `gemini_client.py` | Wrapper cho Google Gemini API (rate limiting, retry, prompt templates) |
| 5.2 | `market_analyzer.py` | Phân tích context thị trường bằng AI |
| 5.3 | `sentiment_analyzer.py` | Phân tích sentiment tin tức vàng |
| 5.4 | `insight_generator.py` | Tạo insights bằng ngôn ngữ tự nhiên |

#### AI Analysis Pipeline:

```
┌────────────────────────────────────────────────────────────┐
│                   AI Reasoning Pipeline                     │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  Input:                                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │ ML Predictions│  │ Market Data  │  │ News Headlines│    │
│  │ - Price: $X   │  │ - XAU: $Y    │  │ - "Fed giữ   │    │
│  │ - Trend: ↑70% │  │ - DXY: Z     │  │    lãi suất"  │    │
│  │ - Vol: Med    │  │ - Oil: $W    │  │ - "Vàng tăng  │    │
│  └──────┬───────┘  └──────┬───────┘  │    mạnh..."    │    │
│         │                 │          └──────┬─────────┘    │
│         └─────────────────┴─────────────────┘              │
│                           │                                │
│                  ┌────────▼────────┐                       │
│                  │  Gemini API     │                       │
│                  │                 │                       │
│                  │  Prompt:        │                       │
│                  │  "Phân tích     │                       │
│                  │   thị trường    │                       │
│                  │   vàng dựa trên │                       │
│                  │   dữ liệu..."  │                       │
│                  └────────┬────────┘                       │
│                           │                                │
│  Output:                  │                                │
│  ┌────────────────────────▼────────────────────────┐      │
│  │                                                  │      │
│  │  📊 Market Analysis:                             │      │
│  │  "Giá vàng đang trong xu hướng tăng ngắn hạn   │      │
│  │   do DXY giảm (-0.3%) và Fed signal giữ lãi    │      │
│  │   suất. Tuy nhiên, RSI ở mức 72 cho thấy       │      │
│  │   vàng đang overbought..."                      │      │
│  │                                                  │      │
│  │  💡 Recommendation:                              │      │
│  │  "Nên chờ pullback về vùng $2,300-$2,310 trước  │      │
│  │   khi vào lệnh BUY. Đặt stop-loss tại $2,285"  │      │
│  │                                                  │      │
│  │  ⚠️ Risk Factors:                               │      │
│  │  "1. CPI Mỹ sắp công bố (rủi ro cao)           │      │
│  │   2. Biến động mạnh quanh Fed meeting"          │      │
│  │                                                  │      │
│  └──────────────────────────────────────────────────┘      │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

#### AI sẽ trả lời 4 câu hỏi chính:

| Câu hỏi | Mô tả |
|----------|--------|
| **1. WHAT** | Thị trường đang diễn ra gì? (tóm tắt tình hình) |
| **2. WHY** | Tại sao giá vàng đang tăng/giảm? (phân tích nguyên nhân) |
| **3. WHAT IF** | Các kịch bản có thể xảy ra? (scenario analysis) |
| **4. WHAT TO DO** | Nên làm gì? (lời khuyên đầu tư cụ thể) |

> 🔧 **GA Integration Point #5**: Tạo `ai-market-analysis` skill + `/run-ai-analysis` workflow

---

### Phase 6: API Layer ⏱️ 1-2 sessions

**Mục tiêu**: REST API cho toàn bộ hệ thống

| # | Endpoint | Method | Mô tả |
|---|----------|--------|--------|
| 6.1 | `/api/gold/prices` | GET | Giá vàng hiện tại + lịch sử |
| 6.2 | `/api/gold/xau` | GET | Chi tiết XAU/USD |
| 6.3 | `/api/gold/sjc` | GET | Chi tiết giá SJC |
| 6.4 | `/api/predictions/price` | GET | Dự đoán giá (regression) |
| 6.5 | `/api/predictions/trend` | GET | Dự đoán xu hướng (classification) |
| 6.6 | `/api/predictions/volatility` | GET | Dự đoán biến động |
| 6.7 | `/api/analysis/ai` | GET | Phân tích AI (Gemini) |
| 6.8 | `/api/analysis/sentiment` | GET | Sentiment tin tức |
| 6.9 | `/api/advisor/advice` | GET | Lời khuyên đầu tư tổng hợp |
| 6.10 | `/api/advisor/risk` | GET | Đánh giá rủi ro |
| 6.11 | `/ws/gold/live` | WS | WebSocket realtime price |

> 🔧 **GA Integration Point #6**: Tạo `/run-prediction` workflow

---

### Phase 7: Web Dashboard ⏱️ 2-3 sessions

**Mục tiêu**: Giao diện web hiện đại, chuyên biệt cho vàng

| # | Task | Chi tiết |
|---|------|----------|
| 7.1 | React + Vite setup | Project init, routing, design system |
| 7.2 | Dark theme design | Gold (#FFD700) + Dark (#1a1a2e) color palette |
| 7.3 | Dashboard page | Overview: XAU/USD, SJC, predictions summary |
| 7.4 | XAU Detail page | Candlestick chart, indicators, predictions |
| 7.5 | SJC Detail page | Price chart, XAU-SJC spread |
| 7.6 | AI Analysis page | AI insights, sentiment gauge, scenario cards |
| 7.7 | Advisor page | Investment advice, risk meter, position sizing |
| 7.8 | Responsive + animations | Mobile-friendly, micro-animations |

### UI Concept:

```
┌──────────────────────────────────────────────────────────────┐
│  🥇 Gold Predictor              [XAU: $2,345 ▲+0.8%]  [🌙] │
├────────┬─────────────────────────────────────────────────────┤
│        │                                                     │
│ 📊     │  ┌─────────────────────────────────────────────┐   │
│ Tổng   │  │          Gold Price Chart (Candlestick)     │   │
│ quan   │  │  🕯️ TradingView-style interactive chart     │   │
│        │  │  + Technical Indicators overlay              │   │
│ 🥇     │  └─────────────────────────────────────────────┘   │
│ XAU/   │                                                     │
│ USD    │  ┌────────────┐ ┌────────────┐ ┌────────────┐      │
│        │  │ 📈 Dự đoán │ │ 🔀 Xu hướng│ │ 🌊 Biến   │      │
│ 🇻🇳   │  │ $2,365     │ │ ↑ TĂNG 72% │ │ động: MED  │      │
│ SJC    │  │ ±$15 (7d)  │ │ ↓ Giảm 18% │ │ ATR: $28  │      │
│        │  │ Conf: 78%  │ │ → Side 10% │ │ Vol: 14%  │      │
│ 🤖     │  └────────────┘ └────────────┘ └────────────┘      │
│ AI     │                                                     │
│ Phân   │  ┌─────────────────────────────────────────────┐   │
│ tích   │  │ 🤖 AI Analysis (Gemini)                     │   │
│        │  │                                              │   │
│ 💡     │  │ "Vàng đang test vùng kháng cự $2,350. DXY  │   │
│ Tư     │  │  giảm 0.3% hỗ trợ vàng tăng. Tuy nhiên    │   │
│ vấn    │  │  RSI=72 cho thấy overbought ngắn hạn..."   │   │
│        │  │                                              │   │
│ ⚙️     │  │ 💡 Khuyến nghị: HOLD - Chờ pullback $2,310 │   │
│ Cài    │  │ ⚠️ Rủi ro: CPI Mỹ công bố thứ 5 tuần sau  │   │
│ đặt    │  └─────────────────────────────────────────────┘   │
│        │                                                     │
└────────┴─────────────────────────────────────────────────────┘
```

---

### Phase 8: Automation & Polish ⏱️ 1 session

| # | Task | Chi tiết |
|---|------|----------|
| 8.1 | Scheduled jobs | Auto collect data mỗi ngày 8:00 AM |
| 8.2 | Auto retrain | Retrain models mỗi tuần |
| 8.3 | Docker Compose | Backend + Frontend + DB containerized |
| 8.4 | Error handling | Retry logic, fallback, alerting |
| 8.5 | README.md | Project documentation |

---

## 🔧 Antigravity Skills & Workflows Roadmap

### Tổng quan tích hợp GA

```
Phase 1 ──► Skill: gold-data-pipeline      + WF: /collect-gold-data
Phase 3 ──► Skill: feature-engineering
Phase 4 ──► Skill: model-training           + WF: /train-gold-models
            Skill: backtesting              + WF: /backtest-strategy
Phase 5 ──► Skill: ai-market-analysis       + WF: /run-ai-analysis
Phase 6 ──►                                   WF: /run-prediction
```

### Skills chi tiết

#### 1. `gold-data-pipeline` (Phase 1-2)
```yaml
Mục đích: Hướng dẫn Antigravity cách thu thập & xử lý dữ liệu vàng
Nội dung:
  - Cách dùng yfinance lấy XAU/USD, DXY, Oil...
  - Cách scrape giá SJC (selectors, error handling)
  - Data quality checks (missing, outliers, duplicates)
  - Troubleshooting common issues
Scripts:
  - scripts/verify_data.py - Kiểm tra data integrity
```

#### 2. `feature-engineering` (Phase 3)
```yaml
Mục đích: Hướng dẫn cách tạo & quản lý features cho gold prediction
Nội dung:
  - Danh sách tất cả technical indicators và formula
  - Macro features và cách tính
  - Feature selection best practices
  - Cách thêm feature mới vào pipeline
```

#### 3. `model-training` (Phase 4)
```yaml
Mục đích: Hướng dẫn train, evaluate, compare ML models
Nội dung:
  - Walk-forward validation setup
  - Hyperparameter tuning strategies
  - Avoiding look-ahead bias
  - Model comparison metrics
  - When to retrain
Scripts:
  - scripts/train_all.py - Train tất cả models
  - scripts/compare_models.py - So sánh performance
```

#### 4. `ai-market-analysis` (Phase 5)
```yaml
Mục đích: Hướng dẫn sử dụng Gemini API cho market analysis
Nội dung:
  - Gemini API setup & best practices
  - Prompt engineering cho financial analysis
  - Rate limiting & cost management
  - Output parsing & validation
  - Khi nào nên trigger AI analysis
```

#### 5. `backtesting` (Phase 4)
```yaml
Mục đích: Hướng dẫn chạy backtesting & đánh giá strategy
Nội dung:
  - Backtesting methodology
  - Performance metrics (Sharpe, Sortino, MaxDD, Win Rate)
  - Risk management rules
  - Common pitfalls (survivorship bias, overfitting)
```

### Workflows chi tiết

| Workflow | Trigger khi | Các bước |
|----------|------------|----------|
| `/collect-gold-data` | Cần update dữ liệu | 1. Activate venv → 2. Run collectors → 3. Validate data → 4. Report |
| `/train-gold-models` | Cần retrain models | 1. Check data freshness → 2. Build features → 3. Train all → 4. Compare → 5. Save best |
| `/run-prediction` | Cần dự đoán mới | 1. Collect latest data → 2. Build features → 3. Run ensemble → 4. AI analysis → 5. Generate advice |
| `/backtest-strategy` | Đánh giá hiệu quả | 1. Load historical → 2. Run backtest → 3. Calculate metrics → 4. Report |
| `/run-ai-analysis` | Cần AI phân tích | 1. Gather context → 2. Call Gemini → 3. Parse response → 4. Store insights |

---

## ⚠️ User Review Required

> [!IMPORTANT]
> **Disclaimer**: Hệ thống chỉ mang tính chất **tham khảo**, không phải lời khuyên đầu tư chuyên nghiệp.

> [!WARNING]
> **Gemini API Key**: Cậu cần cung cấp Google Gemini API key (free tier có 15 requests/minute). Mình sẽ đọc từ `.env`, KHÔNG hardcode.

### Câu hỏi cần cậu xác nhận:

1. **Gemini API**: Cậu đã có Google Gemini API key chưa? Hay mình hướng dẫn tạo?

2. **Database**: Bắt đầu với SQLite (đơn giản, zero config) rồi upgrade PostgreSQL sau, ok không?

3. **SJC Scraping**: Mình sẽ scrape từ `sjc.com.vn` hoặc `giavang.net`. Cậu có nguồn nào prefer không?

4. **Thời gian dự đoán**: Mình đề xuất dự đoán **1 ngày, 7 ngày, 30 ngày** tới. Cậu thấy ok?

5. **Lịch sử dữ liệu**: Mình sẽ thu thập **5 năm gần nhất** để train. Cậu muốn nhiều hơn không?

---

## ✅ Verification Plan

### Phase 2 - Data Collection
- **Test**: Chạy mỗi collector riêng biệt, kiểm tra format output
- **Validate**: So sánh giá thu thập với giá trên sàn/website gốc
- **Command**: `python -m pytest tests/test_collectors.py -v`

### Phase 4 - ML Models
- **Test**: Walk-forward validation trên 1 năm gần nhất
- **Metrics target**: MAPE < 3% cho price prediction, F1 > 0.6 cho trend
- **Command**: `python scripts/evaluate_models.py`

### Phase 5 - AI Reasoning
- **Test**: Gọi Gemini API với sample data, kiểm tra response format
- **Validate**: Đọc AI output, đánh giá có logic không
- **Manual**: Review AI-generated insights cho 10 ngày test

### Phase 6 - API
- **Test**: Hit tất cả endpoints qua Swagger UI (FastAPI tự generate)
- **Command**: `python -m pytest tests/test_api.py -v`

### Phase 7 - Frontend
- **Test**: Mở browser, kiểm tra tất cả pages
- **Tool**: Dùng browser subagent của Antigravity để verify UI

---

## 🚀 Bước triển khai

```
Ưu tiên: Phase 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8

Mỗi Phase sẽ:
1. Tạo/update Skills & Workflows tương ứng
2. Implement code
3. Test & verify
4. User review
```

Cậu review giúp mình nhé! 🙏
