# Phase 2 Walkthrough: Data Collection

**Plan:** Gold Prediction Master Plan
**Ngày triển khai:** 2026-03-22
**Trạng thái:** ✅ Hoàn thành (News collector cần cải thiện)

---

## 📋 Tóm tắt công việc đã thực hiện

### Task 2.1: XAU/USD Collector
- [x] Implement `xau_collector.py` - thu thập từ yfinance (ticker: GC=F)
- [x] Incremental loading (chỉ fetch ngày mới)
- [x] Upsert logic (update nếu đã tồn tại)
- [x] **Verified: 1257 records** lưu thành công (5 năm lịch sử)
- Files: `backend/app/services/data_collector/xau_collector.py`

### Task 2.2: SJC Collector
- [x] Implement `sjc_collector.py` - scrape từ sjc.com.vn
- [x] XML feed parser (primary) + HTML scraper (fallback)
- [x] Price parsing (nghìn VND → triệu VND)
- Files: `backend/app/services/data_collector/sjc_collector.py`

### Task 2.3: Macro Indicators Collector
- [x] Implement `macro_collector.py` - DXY, USD/VND, Oil, US 10Y, S&P 500
- [x] Incremental loading per indicator
- [x] **Verified: 1300 records** lưu thành công (~260 records/indicator)
- Files: `backend/app/services/data_collector/macro_collector.py`

### Task 2.4: News Collector
- [x] Implement `news_collector.py` - scrape cafef.vn
- [x] Duplicate title detection
- ⚠️ cafef.vn HTML structure thay đổi, cần cập nhật selectors
- Files: `backend/app/services/data_collector/news_collector.py`

### Task 2.5: Data Pipeline
- [x] Implement `data_pipeline.py` - orchestrate tất cả collectors
- [x] `run_all()`, `run_gold_only()`, `run_macro_only()`
- [x] Error handling per collector (1 fail không ảnh hưởng others)
- Files: `backend/app/services/data_collector/data_pipeline.py`

### Task 2.6: Base Collector
- [x] Abstract base class với pipeline: fetch → validate → store
- [x] Data validation (duplicates, NaN, negative prices)
- [x] Incremental loading helper (get_last_date_in_db)
- Files: `backend/app/services/data_collector/base_collector.py`

---

## ⚠️ Issues phát hiện

| Issue | Mức độ | Mô tả | Trạng thái |
|-------|--------|-------|------------|
| News scraping empty | Low | cafef.vn HTML selectors cần cập nhật | ⏳ Sẽ fix sau khi có AI sentiment (Phase 5) |

---

## 🧪 Kết quả Verification

```
=== DATABASE SUMMARY ===
gold_prices:      1257 records  ✅
macro_indicators: 1300 records  ✅
news_articles:    0 records     ⚠️ (cafef HTML changed)

XAU/USD range: ~2021 to 2026-03-20
Incremental test: 0 new records on re-run ✅
```

### Hướng dẫn Manual Test
1. Activate venv: `.\venv\Scripts\Activate.ps1`
2. Chạy pipeline:
   ```python
   import sys; sys.path.insert(0, 'backend')
   from app.services.data_collector.data_pipeline import DataPipeline
   pipeline = DataPipeline()
   results = pipeline.run_all()
   ```

---

## 📁 Files Changed

| File | Action | Description |
|------|--------|-------------|
| `backend/app/services/data_collector/base_collector.py` | Created | Abstract base + validation |
| `backend/app/services/data_collector/xau_collector.py` | Created | XAU/USD from yfinance |
| `backend/app/services/data_collector/sjc_collector.py` | Created | SJC scraping (XML+HTML) |
| `backend/app/services/data_collector/macro_collector.py` | Created | DXY, Oil, Rates, S&P 500 |
| `backend/app/services/data_collector/news_collector.py` | Created | cafef.vn scraping |
| `backend/app/services/data_collector/data_pipeline.py` | Created | Pipeline orchestrator |

---

## ➡️ Next Phase Dependencies

- Phase 3 phụ thuộc vào: gold_prices data (✅), macro_indicators data (✅)
- Phase 3 sẽ implement: Technical indicators, macro features, feature builder pipeline
