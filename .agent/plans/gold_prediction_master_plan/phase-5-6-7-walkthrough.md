# Gold Predictor - Phase 5-7 Walkthrough

## Phase 5: AI Reasoning (Rule-based + Gemini-ready) ✅

### Files Created
| File | Mô tả |
|------|--------|
| `backend/app/services/ai_reasoning/gemini_client.py` | Gemini API wrapper, auto-detect availability, fallback |
| `backend/app/services/ai_reasoning/market_analyzer.py` | Rule-based scoring: RSI/MACD/BB/SMA → recommendation |
| `backend/app/services/advisor/investment_advisor.py` | Tổng hợp ML + TA → lời khuyên đầu tư |

### Scoring System
- RSI (overbought/oversold): ±20 points
- MACD crossover: ±15 points
- Bollinger Band touch: ±10 points
- SMA Golden/Death Cross: ±20 points
- ML trend prediction: ±30 points (weighted by probability)
- **Result**: Score → STRONG_BUY / BUY / HOLD / SELL / STRONG_SELL

---

## Phase 6: API Layer ✅

### Endpoints Verified

| Endpoint | Method | Mô tả | Status |
|----------|--------|--------|--------|
| `/health` | GET | Health check | ✅ |
| `/api/v1/gold/prices` | GET | Giá vàng N ngày | ✅ |
| `/api/v1/gold/latest` | GET | Giá mới nhất | ✅ Verified: $4,574.90 |
| `/api/v1/gold/summary` | GET | Tổng quan DB | ✅ Verified: 1257 XAU + 1300 macro |
| `/api/v1/predictions/{horizon}` | GET | ML prediction | ✅ Auto-train |
| `/api/v1/predictions` | GET | All horizons | ✅ |
| `/api/v1/analysis` | GET | Market analysis | ✅ |
| `/api/v1/advisor` | GET | Lời khuyên đầu tư | ✅ |
| `/api/v1/train` | POST | Train models | ✅ |
| `/api/v1/collect-data` | POST | Thu thập dữ liệu | ✅ |

---

## Phase 7: Web Dashboard ✅

### Stack: React + Vite + Recharts
- Dark theme với gold accents
- Area chart giá vàng 1 năm
- Prediction panel (lazy-load ML on demand)
- Investment advisor panel
- Technical indicators snapshot

### Run Commands
```bash
# Backend
cd backend && python -m uvicorn app.main:app --port 8001

# Frontend 
cd frontend && npm run dev
```
