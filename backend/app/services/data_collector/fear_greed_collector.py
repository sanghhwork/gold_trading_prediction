"""
Gold Predictor - Fear & Greed Index Collector
Thu thập Fear & Greed Index từ Alternative.me API (free).

API: https://api.alternative.me/fng/?limit=30&format=json
Dữ liệu: { value: 0-100, value_classification: "Extreme Fear"/"Greed"/... }

Lưu vào bảng macro_indicators có sẵn (indicator="fear_greed").

Điểm mở rộng tương lai:
- Thêm CNN Fear & Greed (stock market)
- Thêm VIX (CBOE Volatility Index)
"""

from datetime import date, datetime, timedelta
from typing import Optional

import pandas as pd
import requests
from sqlalchemy.orm import Session

from app.services.data_collector.base_collector import BaseCollector
from app.db.models import MacroIndicator
from app.db.database import get_session_factory
from app.utils.logger import get_logger

logger = get_logger(__name__)

FEAR_GREED_API_URL = "https://api.alternative.me/fng/"


class FearGreedCollector(BaseCollector):
    """Thu thập Fear & Greed Index từ Alternative.me."""

    def __init__(self):
        super().__init__("fear_greed")

    def fetch_data(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> pd.DataFrame:
        """
        Fetch Fear & Greed Index.
        API trả về dữ liệu theo ngày, miễn phí, không cần API key.
        """
        # Xác định số ngày cần fetch
        if start_date:
            days = (date.today() - start_date).days
        else:
            # Incremental: check DB
            SessionLocal = get_session_factory()
            db = SessionLocal()
            try:
                last_date = self.get_last_date_in_db(
                    db, MacroIndicator, {"indicator": "fear_greed"}
                )
            finally:
                db.close()

            if last_date:
                days = (date.today() - last_date).days
                if days <= 0:
                    self.logger.info("Fear & Greed Index đã cập nhật")
                    return pd.DataFrame()
            else:
                days = 365  # Lần đầu: lấy 1 năm

        # Limit API: max 365 ngày
        days = min(days, 365)

        self.logger.info(f"Fetching Fear & Greed Index ({days} days)...")

        try:
            response = requests.get(
                FEAR_GREED_API_URL,
                params={"limit": days, "format": "json"},
                timeout=15,
            )
            response.raise_for_status()
            data = response.json()

            if "data" not in data:
                self.logger.warning("API response không có 'data'")
                return pd.DataFrame()

            records = []
            for item in data["data"]:
                try:
                    timestamp = int(item["timestamp"])
                    dt = datetime.utcfromtimestamp(timestamp).date()
                    value = int(item["value"])

                    records.append({
                        "date": dt,
                        "indicator": "fear_greed",
                        "close": value,  # Dùng close = FnG value (0-100)
                        "open": None,
                        "high": None,
                        "low": None,
                        "volume": None,
                    })
                except (KeyError, ValueError) as e:
                    self.logger.warning(f"Lỗi parse FnG item: {e}")
                    continue

            df = pd.DataFrame(records)
            self.logger.info(f"Fear & Greed: {len(df)} records")
            return df

        except requests.RequestException as e:
            self.logger.error(f"Lỗi kết nối Fear & Greed API: {e}")
            return pd.DataFrame()

    def store_data(self, df: pd.DataFrame, db: Session) -> int:
        """Lưu vào macro_indicators (reuse schema)."""
        if df.empty:
            return 0

        count = 0
        for _, row in df.iterrows():
            existing = db.query(MacroIndicator).filter_by(
                date=row["date"],
                indicator="fear_greed"
            ).first()

            if existing:
                existing.close = row["close"]
            else:
                record = MacroIndicator(
                    date=row["date"],
                    indicator="fear_greed",
                    close=row["close"],
                )
                db.add(record)
                count += 1

        return count

    def validate_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validate: Fear & Greed value phải trong range 0-100."""
        if df.empty:
            return df

        original_len = len(df)
        df = df[(df["close"] >= 0) & (df["close"] <= 100)]
        
        dropped = original_len - len(df)
        if dropped > 0:
            self.logger.warning(f"Loại bỏ {dropped} records ngoài range 0-100")

        return df
