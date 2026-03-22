"""
Gold Predictor - Base Collector
Abstract base class cho tất cả data collectors.

Điểm mở rộng tương lai:
- Thêm retry logic với exponential backoff
- Thêm concurrent collection (asyncio)
"""

from abc import ABC, abstractmethod
from datetime import datetime, date, timedelta
from typing import Optional

import pandas as pd
from sqlalchemy.orm import Session

from app.db.database import get_session_factory
from app.utils.logger import get_logger

logger = get_logger(__name__)


class BaseCollector(ABC):
    """Abstract base class cho data collectors."""

    def __init__(self, name: str):
        self.name = name
        self.logger = get_logger(f"collector.{name}")

    @abstractmethod
    def fetch_data(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> pd.DataFrame:
        """
        Thu thập dữ liệu từ nguồn.
        Returns DataFrame với columns tùy loại collector.
        """
        pass

    @abstractmethod
    def store_data(self, df: pd.DataFrame, db: Session) -> int:
        """
        Lưu DataFrame vào database.
        Returns số records đã lưu.
        """
        pass

    def collect_and_store(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> int:
        """
        Pipeline hoàn chỉnh: fetch → validate → store.
        Returns số records đã lưu.
        """
        self.logger.info(f"[{self.name}] Bắt đầu thu thập dữ liệu...")

        # 1. Fetch data
        df = self.fetch_data(start_date, end_date)
        if df is None or df.empty:
            self.logger.warning(f"[{self.name}] Không có dữ liệu mới")
            return 0

        self.logger.info(f"[{self.name}] Đã fetch {len(df)} records")

        # 2. Validate
        df = self.validate_data(df)
        self.logger.info(f"[{self.name}] Sau validate: {len(df)} records")

        # 3. Store
        SessionLocal = get_session_factory()
        db = SessionLocal()
        try:
            count = self.store_data(df, db)
            db.commit()
            self.logger.info(f"[{self.name}] Đã lưu {count} records vào DB")
            return count
        except Exception as e:
            db.rollback()
            self.logger.error(f"[{self.name}] Lỗi lưu DB: {e}")
            raise
        finally:
            db.close()

    def validate_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Validate cơ bản cho tất cả collectors.
        Subclass có thể override để thêm validation riêng.
        """
        original_len = len(df)

        # Drop duplicates
        if "date" in df.columns:
            df = df.drop_duplicates(subset=["date"], keep="last")

        # Drop rows với giá trị NaN ở cột quan trọng
        if "close" in df.columns:
            df = df.dropna(subset=["close"])

        # Kiểm tra giá trị âm
        price_cols = [c for c in ["open", "high", "low", "close", "buy_price", "sell_price"] if c in df.columns]
        for col in price_cols:
            invalid = df[col] < 0
            if invalid.any():
                self.logger.warning(f"[{self.name}] Phát hiện {invalid.sum()} giá trị âm ở cột {col}")
                df = df[~invalid]

        dropped = original_len - len(df)
        if dropped > 0:
            self.logger.info(f"[{self.name}] Đã loại bỏ {dropped} records không hợp lệ")

        return df

    def get_last_date_in_db(self, db: Session, model_class, filter_kwargs: dict) -> Optional[date]:
        """
        Lấy ngày gần nhất đã có trong DB cho 1 source/indicator.
        Dùng để chỉ fetch dữ liệu mới (incremental).
        """
        from sqlalchemy import func
        result = db.query(func.max(model_class.date)).filter_by(**filter_kwargs).scalar()
        return result
