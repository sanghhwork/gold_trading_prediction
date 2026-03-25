# 📋 Kết quả Review Plan: Scheduler Improvement

## ✅ Những điểm Plan làm tốt

| Hạng mục | Đánh giá |
|----------|----------|
| Bối cảnh & vấn đề | ✅ Chính xác. Scheduler đã tồn tại tại [scheduler.py](file:///e:/Work/FinanceTrading/backend/app/scheduler.py) với APScheduler `BackgroundScheduler` (line 17, 62). Health API xác nhận `running: True` nhưng app khởi động lúc 21:25, next collect 08:00 → đúng vấn đề |
| Files đề cập | ✅ Tất cả 3 files (`scheduler.py`, `main.py`, `gold_routes.py`) đều tồn tại và mô tả đúng vai trò |
| Startup catch-up flow | ✅ Flow diagram mô tả logic `_should_collect_on_startup()` rõ ràng, kiểm tra `last_date` XAU/USD rồi so sánh với `last_trading_day` |
| Edge cases table | ✅ Cover 5 edge cases quan trọng: crash loop, internet down, trùng job, weekend, holiday |
| Config hiện tại | ✅ Đúng: `daily_collect_time` và `weekly_retrain_day` đã có trong [config.py](file:///e:/Work/FinanceTrading/backend/app/config.py) (line 43-44) |

---

## ⚠️ Những điểm cần bổ sung/điều chỉnh

### 1. **Catch-up blocking vs non-blocking chưa rõ**

**Vấn đề:** Plan đề cập "chạy trong background thread (không block app startup)" nhưng `main.py` lifespan hiện tại gọi `run_startup_catchup()` **đồng bộ** trong `@asynccontextmanager`. Nếu catch-up chạy sync, nó sẽ **block app startup** cho đến khi thu thập xong (có thể mất 30-60s+ vì phải gọi yfinance, SJC API, News API...).

**Đề xuất:** Nên clarify rõ trong plan:
- Option A: Dùng `threading.Thread(target=_job_collect_data, daemon=True).start()` — không block startup nhưng cần log rõ khi xong
- Option B: Dùng `_scheduler.add_job(_job_collect_data, trigger='date', run_date=datetime.now() + timedelta(seconds=5))` — tận dụng APScheduler, chạy 1 lần sau 5s khi startup

> 💡 **Mình đề xuất Option B** vì tận dụng hạ tầng APScheduler có sẵn, scheduler tự quản lý thread pool, và có cơ chế retry/error handling built-in.

---

### 2. **SJC Collector không backfill được ngày cũ**

**Vấn đề:** [sjc_collector.py](file:///e:/Work/FinanceTrading/backend/app/services/data_collector/sjc_collector.py) luôn fetch giá **hôm nay** (`date.today()` — line 109, 179). Nếu app down từ thứ 4 → thứ 6, catch-up chạy thứ 6 chỉ lấy được giá thứ 6, **mất data thứ 4 và thứ 5**.

Tương tự, [giavang_org_collector.py](file:///e:/Work/FinanceTrading/backend/app/services/data_collector/giavang_org_collector.py) cũng chỉ lấy giá hiện tại.

**Đề xuất:** Ghi chú trong plan rằng đây là **known limitation** — SJC/giavang.org chỉ cung cấp giá realtime, không có historical API. Catch-up chỉ đảm bảo **XAU/USD và macro** được backfill (yfinance hỗ trợ lấy historical date range).

---

### 3. **SQLite concurrent write locking**

**Vấn đề:** Dùng SQLite ([database.py](file:///e:/Work/FinanceTrading/backend/app/db/database.py) line 54 — `check_same_thread=False`) + background thread collect data ghi vào DB. Nếu API request cũng đang ghi DB cùng lúc → **SQLite write lock** (`database is locked` error).

**Đề xuất:** Bổ sung vào edge cases table:

| Edge case | Xử lý |
|-----------|--------|
| SQLite write lock khi concurrent | Scheduler job dùng `db.commit()` riêng (session riêng từ `get_session_factory()`), SQLite auto-retry với `PRAGMA busy_timeout`. Nếu lỗi, job sẽ retry lần sau |

Hiện tại collector tự tạo session riêng trong `collect_and_store()` ([base_collector.py](file:///e:/Work/FinanceTrading/backend/app/services/data_collector/base_collector.py) line 74-86) nên impact không lớn, nhưng nên document.

---

### 4. **Thiếu config cho scheduler enable/disable**

**Vấn đề:** Plan không đề cập config để bật/tắt scheduler. Hiện tại scheduler **luôn chạy** khi app start (kể cả development). Comment trong `main.py` line 27 ghi "production only or if explicitly enabled" nhưng code không check environment.

**Đề xuất:** Thêm config `scheduler_enabled: bool = True` trong `config.py`, check trong `start_scheduler()`:
```python
if not settings.scheduler_enabled:
    logger.info("Scheduler disabled by config")
    return
```
Điều này hữu ích khi dev local không muốn scheduler chạy gây noise.

---

## 📊 Tổng kết

| Tiêu chí | Điểm | Nhận xét |
|----------|------|----------|
| Độ chính xác so với codebase | 9/10 | Files, functions, dependencies đều đúng |
| Độ đầy đủ | 7/10 | Thiếu consideration cho SJC backfill limitation, SQLite locking |
| Thiết kế rõ ràng | 7/10 | Startup catch-up blocking/non-blocking cần clarify |
| Risks coverage | 7/10 | 5 edge cases tốt, thiếu SQLite locking, thiếu enable/disable config |
| Backward compatibility | 10/10 | Chỉ thêm mới, không sửa logic cũ |
| Test plan | 8/10 | 5 test cases rõ ràng, có thể thêm integration test |
| Điểm mở rộng | 9/10 | Thiết kế tách hàm tốt, dễ thêm job sau này |

**Kết luận:** ⚠️ **CẦN BỔ SUNG** — Plan đúng và khả thi, cần bổ sung 4 điểm nhỏ trước khi implement:
1. Clarify blocking/non-blocking startup (đề xuất dùng APScheduler one-off job)
2. Ghi chú SJC backfill limitation
3. Document SQLite concurrent write
4. Thêm config `scheduler_enabled`
