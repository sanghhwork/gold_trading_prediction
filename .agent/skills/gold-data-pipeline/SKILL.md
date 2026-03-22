---
name: gold-data-pipeline
description: Hướng dẫn thu thập, xử lý và lưu trữ dữ liệu giá vàng (XAU/USD, SJC) và macro indicators
---

# 🥇 Gold Data Pipeline Skill

## Tổng quan
Skill này hướng dẫn cách thu thập, validate và lưu trữ dữ liệu giá vàng cho hệ thống Gold Predictor.

## Nguồn dữ liệu

### 1. XAU/USD (yfinance)
```python
import yfinance as yf

# Thu thập giá vàng XAU/USD - 5 năm
gold = yf.download("GC=F", period="5y", interval="1d")
# Columns: Open, High, Low, Close, Volume
```

**Tickers quan trọng** (xem `backend/app/utils/constants.py`):
- `GC=F` - Gold Futures (XAU/USD)
- `DX-Y.NYB` - US Dollar Index (DXY)
- `VND=X` - USD/VND exchange rate
- `CL=F` - Crude Oil WTI
- `^TNX` - US 10-Year Treasury Yield
- `^GSPC` - S&P 500

### 2. SJC Gold (Web Scraping)
```python
import requests
from bs4 import BeautifulSoup

# SJC cung cấp XML feed
response = requests.get("https://sjc.com.vn/xml/tygiavang.xml")
# Parse XML để lấy giá mua/bán
```

### 3. Macro Indicators
Tất cả macro indicators đều thu thập từ yfinance cùng cách với XAU/USD.

## Cấu trúc code

| File | Mô tả |
|------|--------|
| `backend/app/services/data_collector/base_collector.py` | Abstract base class cho tất cả collectors |
| `backend/app/services/data_collector/xau_collector.py` | Thu thập XAU/USD từ yfinance |
| `backend/app/services/data_collector/sjc_collector.py` | Scrape giá SJC |
| `backend/app/services/data_collector/macro_collector.py` | Thu thập DXY, Oil, Rates |
| `backend/app/services/data_collector/news_collector.py` | Thu thập tin tức vàng |

## Database Tables

| Table | Dùng cho |
|-------|----------|
| `gold_prices` | Giá XAU/USD (OHLCV) + SJC (mua/bán) |
| `macro_indicators` | DXY, Oil, USD/VND, US 10Y, S&P 500 |
| `news_articles` | Tin tức vàng + sentiment |

## Data Quality Checks

Sau khi thu thập, LUÔN kiểm tra:
1. **Missing dates**: Ngày giao dịch phải liên tục (trừ weekends/holidays)
2. **Outliers**: Giá biến động > 10% trong 1 ngày → flag để review
3. **Duplicates**: Không có duplicate trên (date, source)
4. **Data types**: Tất cả prices phải là float > 0

## Troubleshooting

### yfinance không trả về data
- Kiểm tra kết nối internet
- Thử đổi ticker (GC=F ↔ XAUUSD=X)
- yfinance có rate limit, chờ 1-2 phút rồi thử lại

### SJC scraping bị block
- Thêm User-Agent header
- Giảm tần suất scrape (tối thiểu 60s giữa các request)
- Kiểm tra URL có thay đổi không

### Dữ liệu bị thiếu (missing)
- Weekends/holidays: Bình thường, forward-fill giá cuối cùng
- Gap > 3 ngày liên tiếp: Log warning + investigate
