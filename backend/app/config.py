"""
Gold Predictor - Application Configuration
Đọc cấu hình từ .env file sử dụng pydantic-settings.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings - loaded from .env file."""

    # ===== Application =====
    app_name: str = Field(default="GoldPredictor", description="Tên ứng dụng")
    app_env: str = Field(default="development", description="Môi trường: development/staging/production")
    debug: bool = Field(default=True, description="Chế độ debug")

    # ===== Database =====
    database_url: str = Field(
        default="sqlite:///./data/gold_predictor.db",
        description="Database connection string"
    )

    # ===== AI Reasoning =====
    gemini_api_key: Optional[str] = Field(default=None, description="Google Gemini API key")
    deepseek_api_key: Optional[str] = Field(default=None, description="DeepSeek API key (backup)")

    # ===== Data Collection APIs =====
    alpha_vantage_api_key: Optional[str] = Field(default=None, description="Alpha Vantage API key")
    fred_api_key: Optional[str] = Field(default=None, description="FRED API key")
    
    # ===== Data Collection Resilience =====
    collector_max_retries: int = Field(default=3, description="Số lần retry tối đa cho collectors")
    collector_retry_delay: float = Field(default=2.0, description="Delay (s) retry cơ bản")
    alpha_vantage_call_delay: float = Field(default=15.0, description="Rate limit pause cho Alpha Vantage")

    # ===== Data Collection =====
    sjc_scrape_interval: int = Field(default=60, description="SJC scraping interval (minutes)")
    historical_years: int = Field(default=5, description="Số năm lịch sử thu thập")

    # ===== API =====
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, description="API port")
    cors_origins: str = Field(
        default="http://localhost:5173,http://localhost:3000",
        description="CORS allowed origins (comma-separated)"
    )

    # ===== Scheduler =====
    scheduler_enabled: bool = Field(default=True, description="Bật/tắt scheduler tự động")
    daily_collect_time: str = Field(default="08:00", description="Giờ thu thập dữ liệu hàng ngày (HH:MM)")
    weekly_retrain_day: int = Field(default=0, description="Ngày retrain hàng tuần (0=Monday)")

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins string thành list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


@lru_cache()
def get_settings() -> Settings:
    """
    Singleton pattern cho Settings.
    Sử dụng lru_cache để chỉ load .env 1 lần.
    
    Điểm mở rộng tương lai:
    - Thêm validation cho API keys khi chuyển sang production
    - Thêm config cho multiple AI providers
    """
    return Settings()
