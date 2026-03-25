"""
Gold Predictor - Scheduler
Tự động hóa thu thập dữ liệu và retrain models.

Jobs:
- Daily 8:00 AM: Thu thập dữ liệu mới (XAU, Macro, News)
- Weekly Monday 9:00 AM: Retrain ML models
- Startup catch-up: Nếu data XAU/USD cũ hơn 1 ngày giao dịch → collect ngay

Điểm mở rộng tương lai:
- Thêm webhook notifications (Telegram, Slack)
- Thêm health check monitoring
- Thêm custom schedule qua API
"""

from datetime import datetime, date, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

_scheduler: BackgroundScheduler | None = None
_is_collecting: bool = False


def _job_collect_data():
    """Job: Thu thập dữ liệu hàng ngày.
    
    Sử dụng flag _is_collecting để tránh chạy trùng
    khi startup catch-up và scheduled job overlap.
    """
    global _is_collecting

    if _is_collecting:
        logger.warning("⏰ [SCHEDULER] Collection đang chạy, skip lần này")
        return

    _is_collecting = True
    logger.info("⏰ [SCHEDULER] Bắt đầu thu thập dữ liệu tự động...")
    try:
        from app.services.data_collector.data_pipeline import DataPipeline
        pipeline = DataPipeline()
        results = pipeline.run_all()
        logger.info(f"⏰ [SCHEDULER] Thu thập xong: {results}")
    except Exception as e:
        logger.error(f"⏰ [SCHEDULER] Lỗi thu thập dữ liệu: {e}")
    finally:
        _is_collecting = False


def _job_retrain_models():
    """Job: Retrain models hàng tuần."""
    logger.info("⏰ [SCHEDULER] Bắt đầu retrain models...")
    try:
        from app.services.models.model_trainer import ModelTrainer
        trainer = ModelTrainer()
        results = trainer.train_all_horizons()
        logger.info(f"⏰ [SCHEDULER] Retrain xong: {list(results.keys())}")
    except Exception as e:
        logger.error(f"⏰ [SCHEDULER] Lỗi retrain: {e}")


# ===== Startup Catch-up Logic =====

def _get_last_trading_day() -> date:
    """Lấy ngày giao dịch gần nhất (skip weekend).
    
    - Nếu hôm nay là weekday → return hôm nay
    - Nếu Saturday → return Friday
    - Nếu Sunday → return Friday
    
    Lưu ý: Không xử lý holidays (US market holidays).
    yfinance sẽ trả rỗng nếu là holiday → collector xử lý bình thường.
    """
    today = date.today()
    weekday = today.weekday()
    
    if weekday == 5:  # Saturday
        return today - timedelta(days=1)
    elif weekday == 6:  # Sunday
        return today - timedelta(days=2)
    return today


def _should_collect_on_startup() -> bool:
    """Kiểm tra XAU/USD data có cũ hơn 1 ngày giao dịch không.
    
    Returns:
        True nếu cần collect data ngay khi startup.
    """
    try:
        from app.db.database import get_session_factory
        from app.db.models import GoldPrice
        from sqlalchemy import func

        SessionLocal = get_session_factory()
        db = SessionLocal()
        try:
            last_date = db.query(func.max(GoldPrice.date)).filter_by(
                source="xau_usd"
            ).scalar()
        finally:
            db.close()

        if last_date is None:
            logger.info("⏰ [SCHEDULER] DB trống, cần fetch data lần đầu")
            return True

        last_trading_day = _get_last_trading_day()

        if last_date < last_trading_day:
            logger.info(
                f"⏰ [SCHEDULER] Data cũ: last={last_date}, "
                f"expected={last_trading_day} → cần catch-up"
            )
            return True

        logger.info(f"⏰ [SCHEDULER] Data đã mới (last={last_date}), skip catch-up")
        return False

    except Exception as e:
        logger.error(f"⏰ [SCHEDULER] Lỗi kiểm tra startup catch-up: {e}")
        # An toàn: nếu lỗi thì không collect để tránh startup chậm
        return False


def schedule_startup_catchup():
    """Schedule one-off catch-up job nếu data cũ.
    
    Dùng APScheduler one-off job (run_date) thay vì gọi trực tiếp,
    để KHÔNG block app startup. Job sẽ chạy sau 5 giây.
    
    Known limitation:
    - SJC collector chỉ fetch giá hôm nay, không backfill ngày cũ
    - Chỉ XAU/USD và macro indicators mới backfill được qua yfinance
    """
    if _scheduler is None:
        logger.warning("⏰ [SCHEDULER] Scheduler chưa start, không thể schedule catch-up")
        return

    if not _should_collect_on_startup():
        return

    _scheduler.add_job(
        _job_collect_data,
        trigger='date',
        run_date=datetime.now() + timedelta(seconds=5),
        id="startup_catchup",
        name="Startup Data Catch-up",
        replace_existing=True,
    )
    logger.info("⏰ [SCHEDULER] Đã schedule startup catch-up (chạy sau 5s)")


# ===== Scheduler Lifecycle =====

def start_scheduler():
    """Khởi động scheduler với các jobs đã cấu hình."""
    global _scheduler

    if _scheduler is not None:
        logger.warning("Scheduler đã đang chạy")
        return

    settings = get_settings()

    # Check config enable/disable
    if not settings.scheduler_enabled:
        logger.info("⏰ Scheduler disabled by config (SCHEDULER_ENABLED=false)")
        return

    _scheduler = BackgroundScheduler()

    # Parse schedule config
    collect_time = settings.daily_collect_time or "08:00"
    collect_hour, collect_minute = collect_time.split(":")
    retrain_day = settings.weekly_retrain_day or 0  # 0 = Monday

    day_map = {0: "mon", 1: "tue", 2: "wed", 3: "thu", 4: "fri", 5: "sat", 6: "sun"}
    retrain_day_name = day_map.get(int(retrain_day), "mon")

    # Job 1: Daily data collection (8:00 AM mỗi ngày)
    _scheduler.add_job(
        _job_collect_data,
        trigger=CronTrigger(hour=int(collect_hour), minute=int(collect_minute)),
        id="daily_collect",
        name="Daily Data Collection",
        replace_existing=True,
    )

    # Job 2: Weekly model retrain (9:00 AM mỗi tuần)
    _scheduler.add_job(
        _job_retrain_models,
        trigger=CronTrigger(day_of_week=retrain_day_name, hour=9, minute=0),
        id="weekly_retrain",
        name="Weekly Model Retrain",
        replace_existing=True,
    )

    _scheduler.start()
    logger.info(
        f"⏰ Scheduler started: "
        f"collect daily@{collect_time}, "
        f"retrain weekly@{retrain_day_name} 09:00"
    )


def stop_scheduler():
    """Dừng scheduler."""
    global _scheduler
    if _scheduler:
        _scheduler.shutdown()
        _scheduler = None
        logger.info("⏰ Scheduler stopped")


def get_scheduler_status() -> dict:
    """Lấy trạng thái scheduler."""
    if _scheduler is None:
        settings = get_settings()
        return {
            "running": False,
            "enabled": settings.scheduler_enabled,
            "jobs": [],
        }

    jobs = []
    for job in _scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": str(job.next_run_time) if job.next_run_time else None,
            "trigger": str(job.trigger),
        })

    return {
        "running": _scheduler.running,
        "enabled": True,
        "is_collecting": _is_collecting,
        "jobs": jobs,
    }


def trigger_collect_now() -> dict:
    """Trigger thu thập dữ liệu ngay lập tức (manual).
    
    Returns:
        dict với status và message.
    """
    if _is_collecting:
        return {
            "status": "skipped",
            "message": "Thu thập dữ liệu đang chạy, vui lòng đợi",
        }

    if _scheduler is None:
        # Scheduler không chạy, chạy trực tiếp trong thread mới
        import threading
        thread = threading.Thread(target=_job_collect_data, daemon=True)
        thread.start()
        return {
            "status": "started",
            "message": "Đã bắt đầu thu thập dữ liệu (scheduler disabled, chạy thread riêng)",
        }

    # Dùng APScheduler one-off job
    _scheduler.add_job(
        _job_collect_data,
        trigger='date',
        run_date=datetime.now() + timedelta(seconds=1),
        id="manual_collect",
        name="Manual Data Collection",
        replace_existing=True,
    )

    return {
        "status": "scheduled",
        "message": "Đã schedule thu thập dữ liệu (chạy sau 1s)",
    }
