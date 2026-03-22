"""
Gold Predictor - XAU/USD Collector
Thu thập giá vàng XAU/USD từ yfinance.

Nguồn: Yahoo Finance (ticker: GC=F)
Dữ liệu: OHLCV daily, lịch sử 5+ năm
"""

from datetime import date, timedelta
from typing import Optional

import pandas as pd
import yfinance as yf
from sqlalchemy.orm import Session
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.services.data_collector.base_collector import BaseCollector
from app.db.models import GoldPrice
from app.db.database import get_session_factory
from app.utils.constants import TICKER_XAU_USD
from app.utils.logger import get_logger

logger = get_logger(__name__)


class XAUCollector(BaseCollector):
    """Thu thập giá vàng XAU/USD từ yfinance."""

    def __init__(self):
        super().__init__("xau_usd")
        self.ticker = TICKER_XAU_USD
        self.source = "xau_usd"

    def fetch_data(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> pd.DataFrame:
        """
        Fetch XAU/USD OHLCV data từ yfinance.
        Nếu không có start_date, kiểm tra DB lấy incremental.
        Nếu DB trống, fetch 5 năm lịch sử.
        """
        # Xác định khoảng thời gian cần fetch
        if start_date is None:
            # Kiểm tra ngày cuối trong DB
            SessionLocal = get_session_factory()
            db = SessionLocal()
            try:
                last_date = self.get_last_date_in_db(
                    db, GoldPrice, {"source": self.source}
                )
            finally:
                db.close()

            if last_date:
                # Incremental: fetch từ ngày cuối + 1
                start_date = last_date + timedelta(days=1)
                self.logger.info(f"Incremental fetch từ {start_date}")
            else:
                # Full: fetch 5 năm
                start_date = date.today() - timedelta(days=365 * 5)
                self.logger.info(f"Full fetch từ {start_date}")

        if end_date is None:
            end_date = date.today()

        # Không fetch nếu start_date >= end_date
        if start_date >= end_date:
            self.logger.info("Dữ liệu đã cập nhật, không cần fetch mới")
            return pd.DataFrame()

        self.logger.info(
            f"Đang fetch XAU/USD từ yfinance: {start_date} → {end_date}"
        )

        try:
            ticker = yf.Ticker(self.ticker)
            df = ticker.history(
                start=start_date.isoformat(),
                end=(end_date + timedelta(days=1)).isoformat(),
                interval="1d",
            )

            if df.empty:
                self.logger.warning("yfinance trả về DataFrame rỗng")
                return pd.DataFrame()

            # Chuẩn hóa columns
            df = df.reset_index()
            df = df.rename(columns={
                "Date": "date",
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Volume": "volume",
            })

            # Chỉ giữ columns cần thiết
            keep_cols = ["date", "open", "high", "low", "close", "volume"]
            df = df[[c for c in keep_cols if c in df.columns]]

            # Convert date
            df["date"] = pd.to_datetime(df["date"]).dt.date
            df["source"] = self.source

            self.logger.info(f"Đã fetch {len(df)} records XAU/USD")
            return df

        except Exception as e:
            self.logger.error(f"Lỗi fetch XAU/USD từ yfinance: {e}")
            raise

    def store_data(self, df: pd.DataFrame, db: Session) -> int:
        """
        Lưu XAU/USD data vào bảng gold_prices.
        Sử dụng upsert (insert or ignore) để tránh duplicate.
        """
        if df.empty:
            return 0

        count = 0
        for _, row in df.iterrows():
            # Kiểm tra đã tồn tại chưa
            existing = db.query(GoldPrice).filter_by(
                date=row["date"],
                source=row["source"]
            ).first()

            if existing:
                # Update
                existing.open = row.get("open")
                existing.high = row.get("high")
                existing.low = row.get("low")
                existing.close = row["close"]
                existing.volume = row.get("volume")
            else:
                # Insert
                record = GoldPrice(
                    date=row["date"],
                    source=row["source"],
                    open=row.get("open"),
                    high=row.get("high"),
                    low=row.get("low"),
                    close=row["close"],
                    volume=row.get("volume"),
                )
                db.add(record)
                count += 1

        return count
