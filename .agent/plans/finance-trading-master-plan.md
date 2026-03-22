# 📊 FinanceTrading - Master Plan
# Hệ thống dự đoán biến động thị trường tài chính Việt Nam

---

## 🎯 Tổng quan

Xây dựng hệ thống dự đoán biến động thị trường tài chính tập trung vào:
- **Cổ phiếu Việt Nam** (HOSE, HNX) - dự đoán giá từng mã cụ thể
- **VN-Index** - dự đoán xu hướng chung thị trường
- **Giá vàng** - XAU/USD (thế giới) + SJC (Việt Nam)

### Loại dự đoán:
| Loại | Mô tả | Output |
|------|--------|--------|
| 📈 **Price Regression** | Dự đoán giá cụ thể (1 ngày, 1 tuần, 1 tháng) | Giá dự đoán ± confidence interval |
| 🔀 **Trend Classification** | Dự đoán xu hướng (Tăng / Giảm / Sideway) | Xác suất % mỗi xu hướng |
| 🌊 **Volatility Analysis** | Dự đoán mức biến động | Volatility score + risk level |
| 💡 **Investment Advice** | Lời khuyên đầu tư | Buy/Sell/Hold + risk analysis |

---

## 📡 Nguồn dữ liệu đề xuất

### Dữ liệu miễn phí (Free)

| Nguồn | Loại dữ liệu | Thư viện Python | Ghi chú |
|-------|--------------|-----------------|---------|
| **vnstock** | Cổ phiếu VN, VN-Index, tài chính DN | `vnstock` | ⭐ Tốt nhất cho thị trường VN, dữ liệu từ SSI/TCBS/VCI |
| **yfinance** | XAU/USD, stock quốc tế, VN stocks | `yfinance` | Tốt cho giá vàng thế giới (ticker: `GC=F`) |
| **SJC Website** | Giá vàng SJC | `requests` + `BeautifulSoup` | Cần scraping, cập nhật theo giờ |
| **cafef.vn** | Tin tức tài chính VN | `requests` + `BeautifulSoup` | Dùng cho Sentiment Analysis |

### Chiến lược thu thập dữ liệu

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐     ┌──────────────┐
│  vnstock    │     │  yfinance    │     │ SJC Scraper │     │ News Scraper │
│ (Stocks,    │     │ (XAU/USD,   │     │ (Gold SJC)  │     │ (Sentiment)  │
│  VN-Index)  │     │  Forex)     │     │             │     │              │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘     └──────┬───────┘
       │                   │                   │                   │
       └───────────────────┴───────────────────┴───────────────────┘
                                   │
                          ┌────────▼────────┐
                          │  Data Pipeline  │
                          │  (Clean, Store) │
                          └────────┬────────┘
                                   │
                          ┌────────▼────────┐
                          │   Database      │
                          │  (PostgreSQL)   │
                          └─────────────────┘
```

---

## 🏗️ Kiến trúc hệ thống

```
┌──────────────────────────────────────────────────────────────────────┐
│                        FinanceTrading System                         │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐  ┌───────────┐ │
│  │ Data Layer  │→ │ Feature Eng. │→ │  ML Models  │→ │ Advisor   │ │
│  │             │  │              │  │             │  │           │ │
│  │ • Collectors│  │ • Technical  │  │ • XGBoost   │  │ • Buy/    │ │
│  │ • Cleaners  │  │   Indicators │  │ • LSTM/GRU  │  │   Sell/   │ │
│  │ • Storage   │  │ • Fundamental│  │ • Prophet   │  │   Hold    │ │
│  │             │  │ • Sentiment  │  │ • GARCH     │  │ • Risk    │ │
│  │             │  │ • Calendar   │  │ • Ensemble  │  │ • Sizing  │ │
│  └─────────────┘  └──────────────┘  └──────┬──────┘  └───────────┘ │
│                                            │                        │
│                                    ┌───────▼───────┐                │
│                                    │  FastAPI      │                │
│                                    │  REST API     │                │
│                                    └───────┬───────┘                │
│                                            │                        │
│                                    ┌───────▼───────┐                │
│                                    │  React Web    │                │
│                                    │  Dashboard    │                │
│                                    └───────────────┘                │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Tech Stack

### Backend
| Công cụ | Vai trò |
|---------|---------|
| **Python 3.11+** | Ngôn ngữ chính |
| **FastAPI** | REST API framework |
| **SQLAlchemy** | ORM cho database |
| **PostgreSQL** | Database (SQLite cho dev) |
| **APScheduler** | Job scheduling (tự động thu thập dữ liệu) |

### Machine Learning
| Công cụ | Vai trò |
|---------|---------|
| **scikit-learn** | Classical ML (Random Forest, SVM) |
| **XGBoost / LightGBM** | Gradient Boosting models |
| **TensorFlow/Keras** | Deep Learning (LSTM, GRU) |
| **Prophet** | Time-series forecasting |
| **arch** | GARCH volatility model |
| **ta** | Technical Analysis indicators |

### Data
| Công cụ | Vai trò |
|---------|---------|
| **pandas / numpy** | Data manipulation |
| **vnstock** | Vietnam stock data |
| **yfinance** | Global market data |
| **BeautifulSoup** | Web scraping (SJC, news) |

### Frontend
| Công cụ | Vai trò |
|---------|---------|
| **React (Vite)** | UI Framework |
| **Recharts / TradingView Widget** | Charts & visualization |
| **Ant Design** | UI Component library |

---

## 📁 Cấu trúc dự án

```
FinanceTrading/
├── .agent/
│   ├── docs/                           # Tài liệu kỹ thuật
│   ├── plans/                          # Kế hoạch triển khai
│   ├── workflows/                      # Antigravity workflows
│   └── skills/                         # Antigravity skills
│       ├── financial-data-collection/  # Skill thu thập dữ liệu
│       ├── feature-engineering/        # Skill xử lý features
│       ├── model-training/             # Skill train models
│       ├── backtesting/               # Skill backtesting
│       └── market-analysis/           # Skill phân tích thị trường
│
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI entry point
│   │   ├── config.py                  # Config & environment
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   ├── stocks.py          # API cổ phiếu
│   │   │   │   ├── gold.py            # API giá vàng
│   │   │   │   ├── index_routes.py    # API VN-Index
│   │   │   │   └── advisor.py         # API lời khuyên đầu tư
│   │   │   └── schemas/               # Pydantic schemas
│   │   ├── services/
│   │   │   ├── data_collector/
│   │   │   │   ├── base_collector.py  # Abstract base collector
│   │   │   │   ├── stock_collector.py # Thu thập dữ liệu cổ phiếu
│   │   │   │   ├── gold_collector.py  # Thu thập giá vàng
│   │   │   │   ├── index_collector.py # Thu thập VN-Index
│   │   │   │   └── news_collector.py  # Thu thập tin tức
│   │   │   ├── feature_engine/
│   │   │   │   ├── technical_indicators.py  # RSI, MACD, BB...
│   │   │   │   ├── fundamental_features.py  # P/E, P/B, EPS...
│   │   │   │   └── feature_builder.py       # Pipeline xây features
│   │   │   ├── models/
│   │   │   │   ├── base_model.py            # Abstract model
│   │   │   │   ├── price_predictor.py       # XGBoost, LSTM regression
│   │   │   │   ├── trend_classifier.py      # XGBoost, RF classification
│   │   │   │   ├── volatility_predictor.py  # GARCH, XGBoost volatility
│   │   │   │   └── ensemble.py              # Weighted ensemble
│   │   │   ├── advisor/
│   │   │   │   ├── investment_advisor.py    # Logic tư vấn đầu tư
│   │   │   │   └── risk_assessor.py         # Đánh giá rủi ro
│   │   │   └── backtesting/
│   │   │       └── backtester.py            # Backtesting engine
│   │   ├── db/
│   │   │   ├── database.py                  # DB connection
│   │   │   └── models.py                    # SQLAlchemy models
│   │   └── utils/
│   │       ├── logger.py                    # Logging utility
│   │       └── constants.py                 # Hằng số
│   ├── requirements.txt
│   ├── alembic/                             # DB migrations
│   └── tests/                               # Unit & integration tests
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── charts/                      # Chart components
│   │   │   ├── dashboard/                   # Dashboard layouts
│   │   │   ├── predictions/                 # Prediction displays
│   │   │   └── advisor/                     # Investment advice UI
│   │   ├── pages/
│   │   │   ├── StockPage.jsx               # Trang cổ phiếu
│   │   │   ├── GoldPage.jsx                # Trang giá vàng
│   │   │   ├── IndexPage.jsx               # Trang VN-Index
│   │   │   └── AdvisorPage.jsx             # Trang tư vấn
│   │   ├── services/                        # API calls
│   │   ├── hooks/                           # Custom hooks
│   │   └── utils/                           # Utilities
│   ├── package.json
│   └── vite.config.js
│
├── data/                                    # Local data cache
├── saved_models/                            # Trained ML models
├── notebooks/                               # Jupyter exploration
├── scripts/                                 # Utility scripts
├── .env.example                             # Environment template
├── docker-compose.yml                       # Docker setup
└── README.md                                # Project documentation
```

---

## 📋 Phases triển khai

### Phase 1: Foundation & Data Collection ⏱️ ~2-3 sessions

**Mục tiêu**: Setup project, xây dựng hệ thống thu thập dữ liệu tự động

| Task | Chi tiết |
|------|----------|
| 1.1 | Khởi tạo project Python, cấu hình virtual env, dependencies |
| 1.2 | Tạo database schema (stocks, gold_prices, index_data, predictions) |
| 1.3 | Implement `stock_collector.py` - thu thập OHLCV từ vnstock |
| 1.4 | Implement `gold_collector.py` - XAU/USD (yfinance) + SJC (scraping) |
| 1.5 | Implement `index_collector.py` - VN-Index data |
| 1.6 | Implement `news_collector.py` - thu thập tin tức tài chính |
| 1.7 | Data cleaning & validation pipeline |
| 1.8 | Tạo Antigravity skill: `financial-data-collection` |

---

### Phase 2: Feature Engineering ⏱️ ~2 sessions

**Mục tiêu**: Xây dựng pipeline tính toán features cho ML models

| Task | Chi tiết |
|------|----------|
| 2.1 | Technical indicators: SMA, EMA, RSI, MACD, Bollinger Bands, ATR, OBV, Stochastic, Williams %R |
| 2.2 | Fundamental features (cho stocks): P/E, P/B, EPS, ROE, Market Cap |
| 2.3 | Calendar features: day_of_week, month, quarter, is_month_end |
| 2.4 | Lag features: price_lag_1d, price_lag_5d, price_lag_20d, returns |
| 2.5 | Cross-market correlation features (VN-Index vs Gold, VN-Index vs S&P500) |
| 2.6 | Feature builder pipeline (auto-generate feature matrix) |
| 2.7 | Tạo Antigravity skill: `feature-engineering` |

---

### Phase 3: ML Models ⏱️ ~3-4 sessions

**Mục tiêu**: Train và đánh giá các models dự đoán

| Task | Chi tiết |
|------|----------|
| **Price Prediction (Regression)** | |
| 3.1 | XGBoost/LightGBM regressor - dự đoán giá |
| 3.2 | LSTM/GRU model - time-series price prediction |
| 3.3 | Facebook Prophet - trend decomposition & forecasting |
| **Trend Classification** | |
| 3.4 | XGBoost Classifier - Tăng/Giảm/Sideway classification |
| 3.5 | LSTM Classifier - sequence-based trend prediction |
| **Volatility Prediction** | |
| 3.6 | GARCH model - volatility forecasting |
| 3.7 | XGBoost on volatility features |
| **Ensemble & Evaluation** | |
| 3.8 | Weighted Ensemble model (kết hợp các models) |
| 3.9 | Backtesting framework - đánh giá hiệu quả |
| 3.10 | Model comparison & selection logic |
| 3.11 | Tạo Antigravity skills: `model-training`, `backtesting` |

> ⚠️ **Lưu ý quan trọng**: Mỗi model sẽ được train trên walk-forward validation (không dùng random split cho time-series). Sử dụng metrics: MAE, RMSE, MAPE cho regression; Accuracy, F1, AUC cho classification.

---

### Phase 4: API Layer & Investment Advisor ⏱️ ~2-3 sessions

**Mục tiêu**: Xây dựng REST API và logic tư vấn đầu tư

| Task | Chi tiết |
|------|----------|
| 4.1 | FastAPI setup + CORS configuration |
| 4.2 | API endpoints cho stocks (list, detail, predict, history) |
| 4.3 | API endpoints cho gold (current price, predict, history) |
| 4.4 | API endpoints cho VN-Index (current, predict, history) |
| 4.5 | Investment Advisor engine - combine all predictions |
| 4.6 | Risk Assessment module |
| 4.7 | Advisor API endpoints (get advice, portfolio suggestions) |
| 4.8 | Tạo Antigravity skill: `market-analysis` |

### Investment Advisor Logic:

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│ Price Prediction│     │ Trend Prediction │     │    Volatility   │
│ ($X ± CI)       │     │ (↑70% ↓20% →10%)│     │ (High/Med/Low)  │
└────────┬────────┘     └────────┬─────────┘     └────────┬────────┘
         │                       │                        │
         └───────────────────────┴────────────────────────┘
                                 │
                        ┌────────▼────────┐
                        │ Rule Engine +   │
                        │ Risk Assessment │
                        └────────┬────────┘
                                 │
                    ┌────────────▼────────────┐
                    │   Investment Advice     │
                    │ • Signal: BUY/SELL/HOLD │
                    │ • Confidence: 75%       │
                    │ • Risk Level: Medium    │
                    │ • Target Price: $X      │
                    │ • Stop-Loss: $Y         │
                    │ • Position Size: Z%     │
                    └─────────────────────────┘
```

---

### Phase 5: Web Dashboard ⏱️ ~3-4 sessions

**Mục tiêu**: Giao diện web hiện đại, interactive

| Task | Chi tiết |
|------|----------|
| 5.1 | Init React + Vite project |
| 5.2 | Design system: dark theme, color palette, typography |
| 5.3 | Dashboard homepage: overview cards, mini charts |
| 5.4 | Stock page: search, candlestick chart, predictions, indicators |
| 5.5 | Gold page: live price chart (XAU + SJC), predictions |
| 5.6 | VN-Index page: index chart, prediction, top movers |
| 5.7 | Advisor page: investment advice, risk analysis, portfolio view |
| 5.8 | Responsive design + animations |

### UI Mockup Concept:

```
┌────────────────────────────────────────────────────────────┐
│  🏦 FinanceTrading                    [Search] [🌙/☀️]    │
├──────────┬─────────────────────────────────────────────────┤
│          │                                                 │
│ 📊 Tổng  │  ┌─────────────────────────────────────────┐   │
│    quan  │  │        VN-Index: 1,285.42 ▲ +1.2%      │   │
│          │  │  ┌─────────────────────────────────┐     │   │
│ 📈 Cổ   │  │  │     📈 Interactive Chart         │     │   │
│    phiếu │  │  │     (TradingView style)         │     │   │
│          │  │  └─────────────────────────────────┘     │   │
│ 🥇 Vàng │  ├─────────────────────────────────────────┤   │
│          │  │  Dự đoán   │  Lời khuyên  │  Rủi ro    │   │
│ 🤖 Tư   │  │  Giá: 1290 │  📊 BUY      │  ⚡Medium  │   │
│    vấn   │  │  ±15pts    │  Conf: 72%   │  Vol: 18%  │   │
│          │  │  7 ngày    │  Target:1310 │  SL: 1265  │   │
│ ⚙️ Cài  │  └─────────────────────────────────────────┘   │
│    đặt   │                                                 │
└──────────┴─────────────────────────────────────────────────┘
```

---

### Phase 6: Automation & Polish ⏱️ ~1-2 sessions

| Task | Chi tiết |
|------|----------|
| 6.1 | APScheduler: auto collect data mỗi ngày |
| 6.2 | Auto retrain models hàng tuần |
| 6.3 | Docker Compose setup |
| 6.4 | Monitoring & error alerting |
| 6.5 | Performance optimization |
| 6.6 | README.md documentation |

---

## 🧠 Antigravity Skills

Mình sẽ tạo 5 skills quan trọng để tối ưu khả năng của Antigravity trong repo này:

### Skill 1: `financial-data-collection`
- Hướng dẫn cách thu thập dữ liệu từ vnstock, yfinance
- Cách scrape giá vàng SJC
- Cách xử lý missing data, data quality checks
- Best practices cho financial data pipeline

### Skill 2: `feature-engineering`
- Danh sách tất cả technical indicators và cách tính
- Fundamental analysis features
- Cross-market correlation features
- Feature selection strategies

### Skill 3: `model-training`
- Walk-forward validation cho time-series
- Hyperparameter tuning strategies
- Model evaluation metrics (MAE, RMSE, MAPE, F1, AUC)
- Ensemble techniques
- Avoiding look-ahead bias

### Skill 4: `backtesting`
- Cách backtest trading strategies
- Performance metrics (Sharpe ratio, Max Drawdown, Win Rate)
- Risk management rules
- Position sizing

### Skill 5: `market-analysis`
- Market regime detection
- Investment advice logic
- Risk assessment framework
- Disclaimer và giới hạn của ML predictions

---

## ⚠️ User Review Required

> [!IMPORTANT]
> **Disclaimer pháp lý**: Hệ thống này chỉ mang tính chất **tham khảo**, không phải lời khuyên đầu tư chuyên nghiệp. Mọi quyết định đầu tư cuối cùng thuộc về người dùng. Mình sẽ thêm disclaimer rõ ràng trên giao diện.

> [!WARNING]
> **Độ chính xác ML**: Dự đoán thị trường tài chính là bài toán cực kỳ khó. Không model nào có thể đạt 100% chính xác. Mình sẽ luôn hiển thị **confidence interval** và **risk level** kèm theo mỗi dự đoán.

### Câu hỏi cần cậu xác nhận:

1. **Database**: Cậu muốn dùng PostgreSQL (cho production) hay SQLite trước (đơn giản hơn cho phát triển)?

2. **Deployment**: Cậu sẽ deploy ở đâu? Local machine, VPS, hay cloud (AWS/GCP)?

3. **Scope ban đầu**: Mình đề xuất bắt đầu với **~5-10 mã cổ phiếu phổ biến** (VNM, FPT, VIC, HPG, MBB...) rồi mở rộng sau. Cậu thấy ok không?

4. **Thời gian dự đoán**: Cậu muốn dự đoán theo khoảng thời gian nào? (1 ngày, 1 tuần, 1 tháng, hay tất cả?)

---

## ✅ Verification Plan

### Automated Tests
- Unit tests cho mỗi collector (mock API responses)
- Unit tests cho feature engineering pipeline
- Unit tests cho model predictions (kiểm tra output format)
- Integration tests cho API endpoints
- Backtesting results validation

### Manual Verification
- So sánh dữ liệu thu thập với giá thực trên sàn
- Kiểm tra giao diện web trên browser
- Kiểm tra accuracy của predictions trên dữ liệu test
- Test tất cả API endpoints qua Swagger UI

---

## 🚀 Bước tiếp theo

Sau khi cậu review và confirm plan này, mình sẽ:
1. Bắt đầu Phase 1: Setup project + Data Collection
2. Tạo ngay các Antigravity skills
3. Triển khai tuần tự từng phase

Cậu review giúp mình nhé! 🙏
