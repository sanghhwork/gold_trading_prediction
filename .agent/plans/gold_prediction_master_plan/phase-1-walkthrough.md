# Phase 1 Walkthrough: Project Foundation

**Plan:** Gold Prediction Master Plan
**Ngày triển khai:** 2026-03-22
**Trạng thái:** ✅ Hoàn thành

---

## 📋 Tóm tắt công việc đã thực hiện

### Task 1.1: Python project setup
- [x] Tạo Python venv (Python 3.12.10)
- [x] Tạo `requirements.txt` (40+ packages: FastAPI, SQLAlchemy, yfinance, pandas, loguru...)
- [x] Cài đặt dependencies thành công
- [x] Tạo `.env.example` + `.env`
- [x] Tạo `.gitignore`
- [x] Tạo toàn bộ cấu trúc thư mục (17 `__init__.py` files)
- Files: `requirements.txt`, `.env.example`, `.gitignore`, `backend/app/**/__init__.py`

### Task 1.2: Database schema
- [x] Tạo SQLAlchemy ORM models cho 5 tables:
  - `gold_prices` - Giá XAU/USD (OHLCV) + SJC (mua/bán)
  - `macro_indicators` - DXY, Oil, USD/VND, US 10Y, S&P 500
  - `predictions` - Kết quả dự đoán (price, trend, volatility)
  - `news_articles` - Tin tức + AI sentiment
  - `ai_analyses` - Kết quả phân tích từ Gemini/DeepSeek
- [x] Indexes, unique constraints, proper data types
- [x] Database init thành công (SQLite)
- Files: `backend/app/db/models.py`, `backend/app/db/database.py`

### Task 1.3: Logger & Config
- [x] `config.py` - Pydantic-settings load .env (singleton pattern)
- [x] `logger.py` - Loguru với console + file handlers, error-only log, 30-day retention
- Files: `backend/app/config.py`, `backend/app/utils/logger.py`

### Task 1.4: Constants
- [x] Tất cả yfinance tickers (XAU, DXY, Oil, Rates, USD/VND)
- [x] SJC scraping URLs
- [x] Technical indicator parameters (SMA, EMA, RSI, MACD, BB, ATR...)
- [x] ML model hyperparameters
- [x] Business logic constants (trend labels, risk levels, signals)
- Files: `backend/app/utils/constants.py`

### GA Integration Point #1
- [x] Tạo `gold-data-pipeline` skill (`SKILL.md`)
- [x] Tạo `/collect-gold-data` workflow
- Files: `.agent/skills/gold-data-pipeline/SKILL.md`, `.agent/workflows/collect-gold-data.md`

---

## 🧪 Hướng dẫn Manual Test

### Preconditions
- Python 3.12+ đã cài đặt
- Virtual environment đã activate

### Test Steps
1. Mở terminal tại `e:\Work\FinanceTrading\backend`
2. Chạy FastAPI:
   ```powershell
   e:\Work\FinanceTrading\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```
3. Mở browser: http://127.0.0.1:8000/health
4. Kiểm tra Swagger UI: http://127.0.0.1:8000/docs

### Expected Results
- ✅ Health check trả về: `{"status":"healthy","app":"GoldPredictor","env":"development"}`
- ✅ Swagger UI hiển thị đúng
- ✅ Database file tạo tại `data/gold_predictor.db`

---

## 📁 Files Changed

| File | Action | Description |
|------|--------|-------------|
| `backend/requirements.txt` | Created | Dependencies (40+ packages) |
| `backend/app/main.py` | Created | FastAPI entry point + health check |
| `backend/app/config.py` | Created | Pydantic-settings config |
| `backend/app/db/models.py` | Created | 5 SQLAlchemy ORM tables |
| `backend/app/db/database.py` | Created | DB connection + init |
| `backend/app/utils/logger.py` | Created | Loguru logging |
| `backend/app/utils/constants.py` | Created | All constants |
| `.env.example` | Created | Environment template |
| `.gitignore` | Created | Git ignore rules |
| `.agent/skills/gold-data-pipeline/SKILL.md` | Created | GA skill |
| `.agent/workflows/collect-gold-data.md` | Created | GA workflow |

---

## ➡️ Next Phase Dependencies

- Phase 2 phụ thuộc vào: Database schema (✅), Constants (✅), Logger (✅)
- Phase 2 sẽ implement: `xau_collector.py`, `sjc_collector.py`, `macro_collector.py`
