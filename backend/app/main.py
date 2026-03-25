"""
Gold Predictor - FastAPI Application Entry Point
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.db.database import init_db
from app.utils.logger import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup & shutdown events."""
    # Startup
    logger.info("🥇 Gold Predictor starting up...")
    settings = get_settings()
    
    # Initialize database
    init_db()
    logger.info(f"Environment: {settings.app_env}")
    logger.info(f"Debug mode: {settings.debug}")
    
    # Start scheduler (if enabled in config)
    from app.scheduler import start_scheduler, stop_scheduler, schedule_startup_catchup
    start_scheduler()
    
    # Catch-up: nếu data XAU/USD cũ → schedule one-off collect (non-blocking)
    schedule_startup_catchup()
    
    yield
    
    # Shutdown
    stop_scheduler()
    logger.info("Gold Predictor shutting down...")


def create_app() -> FastAPI:
    """
    Factory function tạo FastAPI app.
    
    Điểm mở rộng tương lai:
    - Thêm API versioning (v1, v2)
    - Thêm rate limiting middleware
    - Thêm authentication middleware
    """
    settings = get_settings()
    
    app = FastAPI(
        title="🥇 Gold Predictor API",
        description="Hệ thống dự đoán giá vàng XAU/USD & SJC với AI Reasoning",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Health check
    @app.get("/health", tags=["System"])
    async def health_check():
        from app.scheduler import get_scheduler_status
        return {
            "status": "healthy",
            "app": settings.app_name,
            "env": settings.app_env,
            "scheduler": get_scheduler_status(),
        }

    # Register API routes
    from app.api.routes.gold_routes import router as gold_router
    app.include_router(gold_router)

    logger.info("FastAPI application created successfully")
    return app


# Application instance
app = create_app()
