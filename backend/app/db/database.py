"""
Gold Predictor - Database Connection
Quản lý kết nối database sử dụng SQLAlchemy async.

Điểm mở rộng tương lai:
- Thêm connection pooling config cho PostgreSQL production
- Thêm health check endpoint cho DB
"""

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.config import get_settings
from app.db.models import Base
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Project root: FinanceTrading/
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent

# Engine & Session factory - khởi tạo lazy
_engine = None
_SessionLocal = None


def _resolve_database_url(url: str) -> str:
    """
    Resolve SQLite relative paths thành absolute paths.
    Đảm bảo data directory tồn tại.
    """
    if url.startswith("sqlite:///./"):
        # Relative path → resolve từ project root
        relative_path = url.replace("sqlite:///./", "")
        absolute_path = PROJECT_ROOT / relative_path
        absolute_path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{absolute_path}"
    return url


def get_engine():
    """
    Lấy SQLAlchemy engine (singleton).
    Tự động tạo nếu chưa có.
    """
    global _engine
    if _engine is None:
        settings = get_settings()
        connect_args = {}
        db_url = _resolve_database_url(settings.database_url)

        # SQLite cần check_same_thread=False cho FastAPI
        if db_url.startswith("sqlite"):
            connect_args["check_same_thread"] = False

        _engine = create_engine(
            db_url,
            connect_args=connect_args,
            echo=settings.debug,  # Log SQL queries in debug mode
        )
        logger.info(f"Database engine created: {db_url.split('://')[0]}://***")

    return _engine


def get_session_factory():
    """Lấy Session factory (singleton)."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            bind=get_engine(),
            autocommit=False,
            autoflush=False,
        )
    return _SessionLocal


def get_db() -> Session:
    """
    Dependency injection cho FastAPI routes.
    
    Usage trong route:
        @router.get("/gold")
        def get_gold(db: Session = Depends(get_db)):
            ...
    """
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Khởi tạo database - tạo tất cả tables nếu chưa có.
    Gọi khi application startup.
    """
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized successfully")


def drop_all_tables():
    """
    Xóa tất cả tables. CHỈ dùng cho testing/development.
    KHÔNG dùng trong production.
    """
    settings = get_settings()
    if settings.is_production:
        logger.error("REFUSED: Cannot drop tables in production!")
        raise RuntimeError("Cannot drop tables in production!")

    engine = get_engine()
    Base.metadata.drop_all(bind=engine)
    logger.warning("All database tables dropped!")
