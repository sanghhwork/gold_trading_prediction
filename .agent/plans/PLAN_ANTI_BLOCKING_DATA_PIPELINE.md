# PLAN: Anti-Blocking Data Pipeline

## Mục tiêu

- Khắc phục hoàn toàn pipeline thu thập dữ liệu đang **down 100%** trên server Digital Ocean
- Xây dựng hệ thống **resilient** với retry logic, fallback sources, error handling
- Đảm bảo hoạt động **lâu dài** trên cloud server bằng cách giảm phụ thuộc scraping

## Non-goals (chưa làm ở phase này)

- Proxy rotation trả phí (budget = free)
- Async collector bằng asyncio (cải tiến sau)
- Full rewrite data pipeline architecture

## Bối cảnh hiện trạng

Pipeline gồm 7 collectors chạy trên Digital Ocean (IP 139.59.104.25), tất cả đều fail:

| Collector | Nguồn | Lỗi | Nguyên nhân |
|-----------|-------|-----|-------------|
| XAU | yfinance (Yahoo) | 0 records | IP cloud bị Yahoo block |
| Macro | yfinance (Yahoo) | Failed get ticker | IP cloud bị Yahoo block |
| SJC | sjc.com.vn + giavang.net | 0 records | IP cloud bị block |
| GiavangOrg | giavang.org | 0 records | IP cloud bị block |
| News | cafef.vn | 404 | URL `cafef.vn/vang.chn` không còn tồn tại |
| FRED | api.stlouisfed.org | Skip | Chưa cấu hình FRED_API_KEY |
| FearGreed | api.alternative.me | ❓ | Chưa rõ, API public thường không block |

### Code hiện tại thiếu:
- **Không retry logic** — fail 1 lần = bỏ cuộc
- **User-Agent tĩnh** — Chrome 120 cứng
- **Không fallback** trên tầng base (chỉ SJC có fallback thủ công)
- **Không rate limiting thông minh** giữa requests

## Yêu cầu nghiệp vụ (đã chốt)

- **Budget**: Free (Option A + C)
- **Hướng giải quyết**: Retry + UA rotation + thêm nguồn fallback API chính thức
- **Ưu tiên**: Khôi phục pipeline càng sớm càng tốt, giải pháp bền vững lâu dài

---

## Thiết kế kỹ thuật / Kiến trúc

### Tổng quan giải pháp

```
┌──────────────────────────────────────────────────┐
│             DataPipeline (orchestrator)           │
└──────────────────┬───────────────────────────────┘
                   │
┌──────────────────▼───────────────────────────────┐
│         BaseCollector (ENHANCED)                  │
│  ✅ Retry with exponential backoff               │
│  ✅ User-Agent rotation pool                     │
│  ✅ Random delay between requests                │
│  ✅ Error categorization (block/network/limit)   │
│  ✅ ResilientSession (shared requests.Session)   │
└──────────────────┬───────────────────────────────┘
                   │
    ┌──────────────┼──────────────┐
    ▼              ▼              ▼
┌────────┐   ┌─────────┐   ┌──────────┐
│  Gold  │   │  Macro  │   │  News &  │
│ Prices │   │Indicators│   │Sentiment │
└───┬────┘   └────┬────┘   └────┬─────┘
    │              │             │
 XAU: yfinance     Macro:       News:
  → AlphaVantage   yfinance →   cafef (URL mới)
                   AlphaVantage  → RSS feeds
 SJC: sjc.com.vn
  → giavang.net    FRED: có key  FearGreed:
  → vang.today     → hoạt động   already OK
  → BTMC API
```

---

## Các thay đổi dự kiến trong code

### Phase 1: Resilience Layer

#### `backend/app/services/data_collector/base_collector.py` (sửa)
- Thêm class `ResilientSession` — wrapper requests.Session với:
  - **Retry logic**: max 3 retries, exponential backoff (2s, 4s, 8s)
  - **User-Agent rotation**: pool 10+ UA strings (Chrome, Firefox, Safari, Edge)
  - **Random delay**: 1-3 giây giữa các requests
  - **Error categorization**: phân loại HTTP 403/429/ConnectionReset → "blocked"
- Thêm method `_get_session()` trong BaseCollector để tất cả collectors dùng chung

#### `backend/app/services/data_collector/http_utils.py` (mới)
- Module chứa: UA pool, ResilientSession class, helper functions
- Tách riêng để dễ test và dễ mở rộng

---

### Phase 2: Fix/Thay thế nguồn dữ liệu

#### `backend/app/services/data_collector/xau_collector.py` (sửa)
- **Giữ yfinance làm primary** (vẫn hoạt động trên máy local)
- **Thêm Alpha Vantage fallback**: nếu yfinance fail → gọi Alpha Vantage API
  - Endpoint: `https://www.alphavantage.co/query?function=GOLD_SILVER_SPOT&symbol=XAU&interval=DAILY`
  - Free tier: 25 calls/ngày, **5 calls/phút** → thêm sleep 15s giữa calls
  - Dùng `requests` trực tiếp (qua `ResilientSession`), KHÔNG thêm package mới
- Logic: `yfinance → Alpha Vantage → raise error`

#### `backend/app/services/data_collector/macro_collector.py` (sửa)
- **Thêm Alpha Vantage fallback** cho từng indicator:
  - DXY: `function=TIME_SERIES_DAILY&symbol=UUP` (UUP ETF proxy cho DXY)
  - USD/VND: `function=CURRENCY_EXCHANGE_RATE&from_currency=USD&to_currency=VND`
  - Oil WTI: `function=WTI` (Commodities endpoint)
  - US 10Y: sử dụng FRED API (nếu có key)
  - S&P 500: `function=TIME_SERIES_DAILY&symbol=SPY`
  - GLD ETF: `function=TIME_SERIES_DAILY&symbol=GLD`
- **Rate limit**: sleep **15 giây** giữa mỗi Alpha Vantage call (5 calls/phút limit)
- Logic: `yfinance → Alpha Vantage (with delay) → skip indicator (log warning)`

#### `backend/app/services/data_collector/sjc_collector.py` (sửa)
- **Thêm vang.today làm fallback**:
  - Endpoint: `https://vang.today/prices.php?type=SJL1L10` (SJC 9999)
  - Response format: `{"success":true, "prices":{"SJL1L10":{"buy":..., "sell":...}}}`
  - Miễn phí, không cần key, cập nhật 5 phút, CORS enabled
- ~~BTMC~~: **bỏ** (cần API key, không phù hợp budget free)
- Chain: `sjc.com.vn → giavang.net → vang.today → empty`
- Sử dụng `ResilientSession` thay vì `requests` trực tiếp

#### `backend/app/services/data_collector/giavang_org_collector.py` (sửa)
- Sử dụng `ResilientSession` với proper headers & retry
- Tăng delay crawl history từ 0.5s → 2-3s (random)
- Thêm referer chain (truy cập trang chính trước → trang con)

#### `backend/app/services/data_collector/news_collector.py` (sửa)
- **Fix URL cafef**: đổi từ `cafef.vn/vang.chn` → `cafef.vn/du-lieu/gia-vang-hom-nay/trong-nuoc.chn`
  - ⚠️ **Lưu ý**: URL mới là trang dữ liệu giá, HTML structure khác → cần **cập nhật CSS selectors** (line 75-76)
  - Kiểm tra selectors phù hợp khi implement, không dùng selectors cũ `.tlitem, .knswli-item`
- **Thêm Google News RSS** làm fallback: `https://news.google.com/rss/search?q=giá+vàng&hl=vi&gl=VN`
- **Thêm Kitco RSS**: `https://www.kitco.com/rss/gold.xml`
- Sử dụng `ResilientSession`

#### `backend/app/services/data_collector/fear_greed_collector.py` (sửa nhẹ)
- Sử dụng `ResilientSession`

#### `backend/app/services/data_collector/fred_collector.py` (sửa nhẹ)
- Sử dụng `ResilientSession`

---

### Phase 3: Config & Monitoring

#### `backend/app/config.py` (sửa)
- Thêm settings **mới** (hiện KHÔNG có trong file):
  - `alpha_vantage_api_key: Optional[str]` — API key Alpha Vantage (free)
  - `fred_api_key: Optional[str]` — **thêm mới** (hiện `fred_collector.py` đọc trực tiếp `os.getenv`)
  - `collector_max_retries: int = 3`
  - `collector_retry_delay: float = 2.0`
  - `alpha_vantage_call_delay: float = 15.0` — delay giữa AV calls (rate limit 5/phút)

#### `backend/app/services/data_collector/fred_collector.py` (sửa nhẹ)
- Đổi từ `os.getenv("FRED_API_KEY")` → đọc qua `get_settings().fred_api_key`
- Nhất quán với pattern config hiện tại

#### `backend/app/utils/constants.py` (sửa)
- Sửa `NEWS_SOURCES["cafef"]` → URL mới `cafef.vn/du-lieu/gia-vang-hom-nay/trong-nuoc.chn`
- Thêm constants:
  - `VANG_TODAY_API_URL = "https://vang.today/prices.php"`
  - `ALPHA_VANTAGE_BASE_URL = "https://www.alphavantage.co/query"`

#### `.env.example` và `.env.production` (sửa)
- Thêm biến `ALPHA_VANTAGE_API_KEY` và `FRED_API_KEY`
- Thêm `COLLECTOR_MAX_RETRIES`, `COLLECTOR_RETRY_DELAY`, `ALPHA_VANTAGE_CALL_DELAY`

---

## Logging & Bảo mật

- Log rõ ràng từng bước retry: `[RETRY 1/3] XAU fetch failed (HTTP 403), retrying in 4s...`
- Log kết quả fallback: `[FALLBACK] XAU: yfinance failed → using Alpha Vantage`
- **KHÔNG log** API keys, chỉ log "API key configured: yes/no"
- Phân loại lỗi rõ ràng trong log: `[BLOCKED]`, `[TIMEOUT]`, `[RATE_LIMIT]`, `[NOT_FOUND]`

## Rủi ro / Edge cases

| Risk | Mô tả | Xử lý |
|------|--------|------|
| **Alpha Vantage rate limit** | Free: 25 calls/ngày, **5 calls/phút** | Pipeline tối đa 7 AV calls/lần run + sleep 15s mỗi call = ~2 phút. Startup + daily = tối đa 14 calls/ngày < 25 |
| **vang.today API down** | Service nhỏ, không SLA | Giữ sjc.com.vn + giavang.net làm tầng fallback trước |
| **cafef URL thay đổi lần nữa** | cafef hay đổi URL | Thêm RSS fallback không phụ thuộc HTML structure |
| **cafef CSS selectors lỗi** | URL mới có HTML structure khác | Cần inspect HTML khi implement, cập nhật selectors phù hợp |
| **Alpha Vantage thay đổi free tier** | Đã giảm từ 500→25 calls/ngày | Giám sát, sẵn sàng chuyển Twelve Data hoặc Stooq |
| **yfinance hoạt động trở lại** | Yahoo có thể unblock | Giữ yfinance làm primary, Alpha Vantage chỉ là fallback |

## Những điểm dễ thay đổi trong tương lai

- **`http_utils.py`**: Dễ thêm proxy rotation sau này — chỉ cần sửa `ResilientSession`
- **Fallback chain**: Mỗi collector dùng pattern `source1 → source2 → source3` — dễ thêm/bớt nguồn
- **Config**: Tất cả thông số retry/delay đều cấu hình qua `.env`
- **Alpha Vantage → Twelve Data/Polygon**: Chỉ cần đổi endpoint trong fallback methods

## Nơi nên tách module/hàm

- `http_utils.py`: Tách riêng logic HTTP resilience, tất cả collectors import từ đây
- `_fetch_alpha_vantage()`: Method riêng trong XAU/Macro collector — dễ test và dễ thay thế
- Mỗi fallback source = 1 private method riêng (`_fetch_sjc_api`, `_fetch_vang_today`, `_fetch_btmc`)

---

## Test plan

### Automated Tests

**Chạy tests hiện có:**
```bash
cd e:\Work\FinanceTrading\backend
..\venv\Scripts\python.exe -m pytest tests/test_collectors.py -v
```

**Tests mới cần viết** (`backend/tests/test_resilience.py`):

1. **Test ResilientSession retry logic**:
   - Mock requests.get trả về 403 → verify retry 3 lần → verify backoff delay
   - Mock requests.get trả về 200 ở lần 2 → verify thành công

2. **Test User-Agent rotation**:
   - Gọi `ResilientSession` 10 lần → verify UA khác nhau được dùng

3. **Test error categorization**:
   - HTTP 403 → "blocked"
   - HTTP 429 → "rate_limited"
   - ConnectionError → "network"
   - HTTP 200 → "success"

4. **Test fallback chain XAU**:
   - Mock yfinance fail → verify Alpha Vantage được gọi
   - Mock cả 2 fail → verify raise error

5. **Test fallback chain SJC**:
   - Mock sjc.com.vn fail → verify giavang.net → vang.today → BTMC

6. **Test cafef URL mới**:
   - Verify URL đổi từ `/vang.chn` sang `/du-lieu/gia-vang-hom-nay/trong-nuoc.chn`

### Manual Verification

**Trên máy local:**
```bash
cd e:\Work\FinanceTrading\backend
..\venv\Scripts\python.exe -c "
from app.services.data_collector.data_pipeline import DataPipeline
pipeline = DataPipeline()
results = pipeline.run_all()
print(results)
"
```

**Trên server Digital Ocean (sau khi deploy):**
```bash
docker exec -it gold-predictor-api python -c "
from app.services.data_collector.data_pipeline import DataPipeline
pipeline = DataPipeline()
results = pipeline.run_all()
print(results)
"
```

> ⚠️ **Quan trọng**: Cần cậu tạo API key Alpha Vantage (free) tại https://www.alphavantage.co/support/#api-key trước khi deploy, và cấu hình `ALPHA_VANTAGE_API_KEY` trong `.env`. Tùy chọn thêm FRED key tại https://fred.stlouisfed.org/docs/api/api_key.html
