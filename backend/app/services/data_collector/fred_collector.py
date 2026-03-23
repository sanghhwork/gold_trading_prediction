"""
Gold Predictor - FRED Data Collector
Thu thập dữ liệu kinh tế vĩ mô từ FRED API (Federal Reserve Economic Data).

Series:
- CPIAUCSL: CPI All Items (Consumer Price Index)
- T5YIE: 5-Year Breakeven Inflation Rate
- DFEDTARU: Fed Funds Rate Upper Target

Lưu vào bảng macro_indicators có sẵn.

API: https://api.stlouisfed.org/fred/series/observations (free, cần API key)

Điểm mở rộng tương lai:
- Thêm unemployment rate (UNRATE)
- Thêm M2 money supply
- Thêm 10Y-2Y Treasury spread
"""

from datetime import date, timedelta
from typing import Optional

import pandas as pd
import requests
from sqlalchemy.orm import Session

from app.services.data_collector.base_collector import BaseCollector
from app.db.models import MacroIndicator
from app.db.database import get_session_factory
from app.utils.logger import get_logger

logger = get_logger(__name__)

FRED_API_BASE = "https://api.stlouisfed.org/fred/series/observations"

# FRED series mapping → indicator name trong DB
FRED_SERIES = {
    "CPIAUCSL": "cpi",
    "T5YIE": "inflation_5y_breakeven",
    "DFEDTARU": "fed_rate",
}


class FREDCollector(BaseCollector):
    """Thu thập macro data từ FRED API."""

    def __init__(self, api_key: str = ""):
        super().__init__("fred")
        self.api_key = api_key
        
        if not self.api_key:
            self._load_api_key()

    def _load_api_key(self):
        """Load FRED API key từ config/env."""
        import os
        self.api_key = os.getenv("FRED_API_KEY", "")
        
        if not self.api_key:
            try:
                from app.config import settings
                self.api_key = getattr(settings, "fred_api_key", "")
            except (ImportError, AttributeError):
                pass
        
        if not self.api_key:
            self.logger.warning(
                "FRED_API_KEY chưa được cấu hình. "
                "Đăng ký miễn phí tại: https://fred.stlouisfed.org/docs/api/api_key.html"
            )

    def fetch_data(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> pd.DataFrame:
        """Fetch tất cả FRED series."""
        if not self.api_key:
            self.logger.error("FRED_API_KEY chưa có, skip FRED collection")
            return pd.DataFrame()

        all_data = []
        for series_id, indicator_name in FRED_SERIES.items():
            try:
                df = self._fetch_series(series_id, indicator_name, start_date, end_date)
                if df is not None and not df.empty:
                    all_data.append(df)
            except Exception as e:
                self.logger.error(f"Lỗi fetch FRED {series_id}: {e}")
                continue

        if not all_data:
            return pd.DataFrame()

        result = pd.concat(all_data, ignore_index=True)
        self.logger.info(f"FRED: Tổng {len(result)} records")
        return result

    def _fetch_series(
        self,
        series_id: str,
        indicator_name: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> pd.DataFrame:
        """Fetch 1 FRED series."""
        # Incremental loading
        if start_date is None:
            SessionLocal = get_session_factory()
            db = SessionLocal()
            try:
                last_date = self.get_last_date_in_db(
                    db, MacroIndicator, {"indicator": indicator_name}
                )
            finally:
                db.close()

            if last_date:
                start_date = last_date + timedelta(days=1)
            else:
                start_date = date.today() - timedelta(days=365 * 5)

        if end_date is None:
            end_date = date.today()

        if start_date >= end_date:
            self.logger.info(f"FRED {series_id} ({indicator_name}): đã cập nhật")
            return pd.DataFrame()

        self.logger.info(f"Fetching FRED {series_id} ({indicator_name}): {start_date} → {end_date}")

        try:
            response = requests.get(
                FRED_API_BASE,
                params={
                    "series_id": series_id,
                    "api_key": self.api_key,
                    "file_type": "json",
                    "observation_start": start_date.isoformat(),
                    "observation_end": end_date.isoformat(),
                },
                timeout=15,
            )
            response.raise_for_status()
            data = response.json()

            if "observations" not in data:
                self.logger.warning(f"FRED {series_id}: không có observations")
                return pd.DataFrame()

            records = []
            for obs in data["observations"]:
                try:
                    value = obs["value"]
                    if value == ".":  # FRED uses "." for missing
                        continue
                    
                    records.append({
                        "date": date.fromisoformat(obs["date"]),
                        "indicator": indicator_name,
                        "close": float(value),
                        "open": None,
                        "high": None,
                        "low": None,
                        "volume": None,
                    })
                except (KeyError, ValueError) as e:
                    self.logger.warning(f"Lỗi parse FRED observation: {e}")
                    continue

            df = pd.DataFrame(records)
            self.logger.info(f"FRED {series_id}: {len(df)} records")
            return df

        except requests.RequestException as e:
            self.logger.error(f"Lỗi kết nối FRED API: {e}")
            return pd.DataFrame()

    def store_data(self, df: pd.DataFrame, db: Session) -> int:
        """Lưu vào macro_indicators."""
        if df.empty:
            return 0

        count = 0
        for _, row in df.iterrows():
            existing = db.query(MacroIndicator).filter_by(
                date=row["date"],
                indicator=row["indicator"]
            ).first()

            if existing:
                existing.close = row["close"]
            else:
                record = MacroIndicator(
                    date=row["date"],
                    indicator=row["indicator"],
                    close=row["close"],
                )
                db.add(record)
                count += 1

        return count
