"""
Gold Predictor - Scheduler
Tự động hóa thu thập dữ liệu và retrain models.

Jobs:
- Daily 8:00 AM: Thu thập dữ liệu mới (XAU, Macro, News)
- Weekly Monday 9:00 AM: Retrain ML models
- Hourly: Thu thập giá SJC (khi có API)

Điểm mở rộng tương lai:
- Thêm webhook notifications (Telegram, Slack)
- Thêm health check monitoring
- Thêm custom schedule qua API
"""

from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

_scheduler: BackgroundScheduler | None = None


def _job_collect_data():
    """Job: Thu thập dữ liệu hàng ngày."""
    logger.info("⏰ [SCHEDULER] Bắt đầu thu thập dữ liệu tự động...")
    try:
        from app.services.data_collector.data_pipeline import DataPipeline
        pipeline = DataPipeline()
        results = pipeline.run_all()
        logger.info(f"⏰ [SCHEDULER] Thu thập xong: {results}")
    except Exception as e:
        logger.error(f"⏰ [SCHEDULER] Lỗi thu thập dữ liệu: {e}")


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


def start_scheduler():
    """Khởi động scheduler với các jobs đã cấu hình."""
    global _scheduler

    if _scheduler is not None:
        logger.warning("Scheduler đã đang chạy")
        return

    settings = get_settings()

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
        return {"running": False, "jobs": []}

    jobs = []
    for job in _scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": str(job.next_run_time) if job.next_run_time else None,
            "trigger": str(job.trigger),
        })

    return {"running": _scheduler.running, "jobs": jobs}
