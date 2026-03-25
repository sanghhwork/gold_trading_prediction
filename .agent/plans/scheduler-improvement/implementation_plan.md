# 🎯 Cải thiện Scheduler - Startup Catch-up & Management APIs

## Bối cảnh & Vấn đề

Scheduler hiện tại (`backend/app/scheduler.py`) đã hoạt động đúng với APScheduler:
- ✅ Daily collection lúc 08:00 AM
- ✅ Weekly retrain lúc 09:00 AM thứ Hai

**Vấn đề**: Khi app khởi động lại, scheduler chỉ đặt lịch cho lần trigger tiếp theo → data bị cũ cho đến 08:00 sáng hôm sau.

---

## Proposed Changes

### Component 1: Scheduler Core

#### [MODIFY] [scheduler.py](file:///e:/Work/FinanceTrading/backend/app/scheduler.py)

**1. Startup catch-up (non-blocking)**

Dùng APScheduler one-off job thay vì gọi trực tiếp — **không block app startup**:

```python
def _schedule_startup_catchup():
    """Kiểm tra data cũ → schedule one-off collect job nếu cần."""
    if not _should_collect_on_startup():
        logger.info("⏰ [SCHEDULER] Data đã cập nhật, skip catch-up")
        return
    
    # One-off job chạy sau 5s, tận dụng APScheduler thread pool
    _scheduler.add_job(
        _job_collect_data,
        trigger='date',
        run_date=datetime.now() + timedelta(seconds=5),
        id="startup_catchup",
        name="Startup Data Catch-up",
        replace_existing=True,
    )
    logger.info("⏰ [SCHEDULER] Đã schedule startup catch-up (5s)")
```

**2. Check logic `_should_collect_on_startup()`**

```python
def _should_collect_on_startup() -> bool:
    """Kiểm tra XAU/USD data có cũ hơn 1 ngày giao dịch không."""
    # Query last_date từ DB
    # So sánh với _get_last_trading_day()
    # Return True nếu chênh > 0
```

**3. Utility `_get_last_trading_day()`**

```python
def _get_last_trading_day() -> date:
    """Lấy ngày giao dịch gần nhất (skip Sat/Sun)."""
    today = date.today()
    if today.weekday() == 5:  # Saturday
        return today - timedelta(days=1)
    elif today.weekday() == 6:  # Sunday
        return today - timedelta(days=2)
    return today
```

**4. Concurrent collection prevention**

```python
_is_collecting = False

def _job_collect_data():
    global _is_collecting
    if _is_collecting:
        logger.warning("⏰ [SCHEDULER] Collection đang chạy, skip")
        return
    _is_collecting = True
    try:
        # ... existing logic ...
    finally:
        _is_collecting = False
```

**5. Config enable/disable**

Check `settings.scheduler_enabled` trong `start_scheduler()` — skip nếu disabled.

---

#### [MODIFY] [config.py](file:///e:/Work/FinanceTrading/backend/app/config.py)

Thêm config:
```python
scheduler_enabled: bool = Field(default=True, description="Bật/tắt scheduler tự động")
```

---

#### [MODIFY] [main.py](file:///e:/Work/FinanceTrading/backend/app/main.py)

Gọi startup catch-up sau `start_scheduler()`:
```python
start_scheduler()  # existing
# Catch-up nếu data cũ (non-blocking, chạy qua APScheduler)
from app.scheduler import schedule_startup_catchup
schedule_startup_catchup()
```

---

### Component 2: Scheduler Management APIs

#### [MODIFY] [gold_routes.py](file:///e:/Work/FinanceTrading/backend/app/api/routes/gold_routes.py)

Thêm 2 endpoints:
- `GET /api/v1/scheduler/status` — trạng thái + danh sách jobs + next run
- `POST /api/v1/scheduler/trigger-collect` — trigger collect ngay

---

## Known Limitations

| Limitation | Chi tiết |
|-----------|----------|
| SJC không backfill | `sjc_collector.py` chỉ fetch giá **hôm nay** (line 109). Nếu miss 2 ngày, data SJC cũ mất vĩnh viễn. Chỉ XAU/USD & macro mới backfill được qua yfinance |
| SQLite concurrent write | Background thread ghi DB cùng lúc API request. Mitigation: collector tự tạo session riêng (`base_collector.py` line 74), SQLite auto-retry. Nếu cần, thêm `PRAGMA busy_timeout=5000` |

---

## Edge cases

| Edge case | Xử lý |
|-----------|--------|
| App restart liên tục (crash loop) | Catch-up check chỉ query 1 record, overhead thấp |
| Internet down khi catch-up | Catch-up fail → log error, scheduled job retry theo lịch |
| Catch-up chạy trùng scheduled job | Flag `_is_collecting` prevent concurrent runs |
| Weekend startup | `_get_last_trading_day()` trả về Friday → skip nếu data đã có |
| Holiday (market closed) | yfinance trả rỗng → collector xử lý bình thường |
| SQLite write lock | Session riêng + auto-retry, log warning nếu lỗi |
| Scheduler disabled | Check `scheduler_enabled` config, log info và return |

---

## Verification Plan

### Automated Tests

```bash
cd e:\Work\FinanceTrading\backend
..\venv\Scripts\python.exe -m pytest tests/ -v
```

Thêm test mới `tests/test_scheduler.py`:
- `test_should_collect_on_startup_with_old_data`
- `test_should_not_collect_when_data_fresh`
- `test_get_last_trading_day_weekday`
- `test_get_last_trading_day_weekend`
- `test_concurrent_collection_prevention`

### Manual Verification

1. Restart app → kiểm tra log `[SCHEDULER] Startup catch-up`
2. `GET /health` → scheduler status
3. `GET /api/v1/scheduler/status` → chi tiết jobs
4. `POST /api/v1/scheduler/trigger-collect` → trigger thủ công
5. Kiểm tra DB → data XAU/USD ngày mới nhất
