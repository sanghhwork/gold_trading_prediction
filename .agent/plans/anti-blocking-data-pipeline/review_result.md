# 📋 Kết quả Review Plan: Anti-Blocking Data Pipeline

**Plan file:** `.agent/plans/PLAN_ANTI_BLOCKING_DATA_PIPELINE.md`
**Ngày review:** 2026-03-25

---

## ✅ Những điểm Plan làm tốt

| Hạng mục | Đánh giá |
|----------|----------|
| **Bối cảnh hiện trạng** | ✅ Chính xác. Đã xác minh 7 collectors đều tồn tại trong `data_collector/`. Pipeline order trong `data_pipeline.py` (line 34-41) khớp chính xác |
| **Kiến trúc Resilience Layer** | ✅ Hợp lý. Tách `http_utils.py` riêng là đúng pattern vì hiện 5 files dùng `import requests` trực tiếp (sjc, news, giavang_org, fred, fear_greed) |
| **Chiến lược fallback** | ✅ Tốt. Mỗi collector có fallback chain rõ ràng, không phụ thuộc 1 source duy nhất |
| **Cafef URL mới** | ✅ **Đã xác minh hoạt động** — `cafef.vn/du-lieu/gia-vang-hom-nay/trong-nuoc.chn` trả về data giá vàng ngày 25/03/2026 |
| **Non-goals** | ✅ Rõ ràng, tránh scope creep (không proxy trả phí, không async, không rewrite) |
| **Logging & Bảo mật** | ✅ Tuân thủ global rules: không log API keys, phân loại lỗi rõ ràng |
| **Test plan** | ✅ Có cả automated tests (mock) và manual verification commands |
| **Điểm mở rộng** | ✅ Thiết kế tốt: `ResilientSession` dễ thêm proxy sau, fallback chain dễ thêm/bớt nguồn |

---

## ⚠️ Những điểm cần bổ sung/điều chỉnh

### 1. **API Endpoints trong plan bị SAI — cần sửa trước khi implement**

**Vấn đề:** 3 API endpoints trong plan không chính xác so với tài liệu thực tế:

| Plan ghi | Thực tế (đã xác minh) | Nguồn |
|----------|----------------------|-------|
| `https://api.vang.today/v1/prices` | `https://vang.today/prices.php` | vang.today/api documentation |
| `btmc.vn/api/bieudo/getpricebyname?name=SJC 1L - 10L` | `api.btmc.vn/api/BTMCAPI/getpricebtmc?key=...` (cần API key) | btmc.vn API docs |
| `alphavantage.co/query?function=FX_DAILY&from_symbol=XAU&to_symbol=USD` | `function=GOLD_SILVER_SPOT&symbol=XAU` hoặc `symbol=GOLD` | Alpha Vantage documentation |

**Đề xuất:**
- Sửa vang.today → `https://vang.today/prices.php?type=SJL1L10` (SJC 9999), response format: `{"success":true, "prices":{"SJL1L10":{"buy":..., "sell":...}}}`
- BTMC cần API key → nếu budget = free, có thể bỏ BTMC hoặc tìm endpoint không cần key. Thay bằng **vang.today** (đã có nhiều đơn vị: SJC, DOJI, PNJ, Bảo Tín...) làm nguồn tổng hợp duy nhất
- Alpha Vantage gold: dùng `GOLD_SILVER_SPOT` thay `FX_DAILY` cho XAU/USD

---

### 2. **`fred_api_key` KHÔNG tồn tại trong `config.py` — plan mô tả sai**

**Vấn đề:** Plan ghi `fred_api_key: Optional[str] — đã có nhưng chưa dùng đúng`. Thực tế, **`fred_api_key` KHÔNG có trong `config.py`** (line 12-64). `FREDCollector` đọc trực tiếp từ `os.getenv("FRED_API_KEY")` tại `fred_collector.py` line 57.

**Đề xuất:** Phải thêm `fred_api_key` vào `config.py` (không phải "sửa"). Và cập nhật `fred_collector.py` để đọc từ Settings thay vì `os.getenv()` trực tiếp → nhất quán với pattern config hiện tại.

---

### 3. **Thiếu đề cập thay đổi `constants.py`**

**Vấn đề:** `constants.py` (line 34-42) chứa hardcoded URLs:
```python
SJC_URL = "https://sjc.com.vn/xml/tygiavang.xml"
SJC_BACKUP_URL = "https://www.sjc.com.vn"
NEWS_SOURCES = {
    "cafef": "https://cafef.vn/vang.chn",  # ← URL cũ, 404!
}
```
Nhưng plan **không đề cập sửa file này**, dù cafef URL cần thay đổi và nên cập nhật URLs tại đây.

**Đề xuất:** Thêm `constants.py` vào danh sách files cần sửa:
- Sửa `NEWS_SOURCES["cafef"]` → URL mới
- Thêm `VANG_TODAY_API_URL`, `ALPHA_VANTAGE_BASE_URL` vào constants

---

### 4. **Alpha Vantage rate limit tính toán chưa đủ chi tiết**

**Vấn đề:** Plan ghi "tối đa 10-12 calls/lần run (XAU + 6 macro = 7 calls)". Nhưng tính chi tiết:
- XAU: 1 call
- Macro: DXY + USD/VND + Oil + US_10Y + S&P500 + GLD = **6 calls**
- Tổng fallback: **7 calls** (nếu TẤT CẢ yfinance fail → tất cả dùng Alpha Vantage)
- Free tier: 25 calls/ngày, **5 calls/phút**

> ⚠️ Nếu chạy 7 calls liên tục → vi phạm 5 calls/phút! Cần thêm delay giữa các Alpha Vantage calls.

**Đề xuất:** Thêm logic:
- Sleep 15-20 giây giữa mỗi Alpha Vantage call
- Hoặc dùng rate limiter trong `ResilientSession` riêng cho Alpha Vantage
- Tính cả trường hợp startup catch-up + daily collect trong cùng ngày = tối đa 14 calls → vẫn dưới 25

---

### 5. **`sentiment_analyzer.py` — impact gián tiếp cần lưu ý**

**Vấn đề:** `SentimentAnalyzer` chạy sau `NewsCollector` trong pipeline (line 122-126 `data_pipeline.py`). Nếu news collection vẫn fail → sentiment cũng fail. Plan có fix news (URL mới + RSS) nhưng **không đề cập xử lý khi tất cả news sources fail** → sentiment sẽ log lỗi.

**Đề xuất:** Thêm note trong plan: nếu news fetch = 0 articles → sentiment analyzer sẽ skip gracefully (KHÔNG phải lỗi). Kiểm tra `analyze_unanalyzed_articles()` đã handle trường hợp 0 articles (line 163-165: đã OK ✅).

---

### 6. **Thiếu `alpha-vantage` Python package trong `requirements.txt`**

**Vấn đề:** Plan đề xuất dùng Alpha Vantage API nhưng không đề cập thêm package vào `requirements.txt`. Có 2 cách tiếp cận:
- Dùng `requests` trực tiếp gọi API → không cần thêm package (khuyên dùng)
- Dùng `alpha_vantage` Python wrapper → cần thêm vào requirements

**Đề xuất:** Clarify trong plan rằng sẽ **dùng `requests` (qua ResilientSession) gọi Alpha Vantage API trực tiếp** → không thêm dependency mới, giữ đơn giản.

---

### 7. **cafef scraping CSS selectors có thể lỗi với URL mới**

**Vấn đề:** `news_collector.py` (line 75) dùng selectors:
```python
news_items = soup.select(".tlitem, .knswli-item, .box-category-item, .item-news")
```
URL mới `cafef.vn/du-lieu/gia-vang-hom-nay/trong-nuoc.chn` có **structure HTML khác** (trang dữ liệu giá, không phải trang tin tức). Cần verify CSS selectors.

**Đề xuất:** Plan cần note: sau khi đổi URL cafef, cần **kiểm tra HTML structure** của trang mới và cập nhật CSS selectors phù hợp. Hoặc xem xét giữ URL cafef cho mục đích **lấy tin tức vàng** (không phải giá), tìm URL tin tức mới thay vì URL dữ liệu giá.

---

## 📊 Tổng kết

| Tiêu chí | Điểm | Nhận xét |
|----------|------|----------|
| Độ chính xác so với codebase | **7/10** | Hầu hết chính xác, nhưng `fred_api_key` trong config mô tả sai, thiếu `constants.py` |
| Độ đầy đủ | **7/10** | Cover tốt collectors, nhưng thiếu `constants.py`, thiếu clarify package strategy |
| Thiết kế rõ ràng | **8/10** | Kiến trúc ResilientSession + fallback chain rõ ràng, dễ implement |
| Risks coverage | **7/10** | Cover tốt risks chính, nhưng thiếu Alpha Vantage per-minute rate limit |
| Backward compatibility | **9/10** | Giữ yfinance làm primary, thêm fallback → không break gì |
| Test plan | **8/10** | Có mock tests + manual, nhưng nên thêm test rate limit handling |
| Điểm mở rộng | **9/10** | Thiết kế module hóa tốt, dễ thêm proxy/nguồn mới |

---

**Kết luận:** ⚠️ **CẦN BỔ SUNG** — Plan có nền tảng tốt nhưng cần sửa **3 API endpoints sai** và bổ sung **4 điểm** trước khi implement.

### 📌 Checklist bổ sung trước khi implement

- [ ] Sửa vang.today endpoint: `/v1/prices` → `/prices.php?type=SJL1L10`
- [ ] Sửa BTMC endpoint hoặc bỏ (cần API key) → dùng vang.today tổng hợp thay thế
- [ ] Sửa Alpha Vantage XAU endpoint: `FX_DAILY` → `GOLD_SILVER_SPOT`
- [ ] Sửa mô tả `fred_api_key`: "thêm mới" thay vì "đã có"
- [ ] Thêm `constants.py` vào danh sách files cần sửa
- [ ] Thêm rate limit delay cho Alpha Vantage (5 calls/phút)
- [ ] Clarify: dùng `requests` trực tiếp cho Alpha Vantage, không thêm package
