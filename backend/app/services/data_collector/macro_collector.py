"""
Gold Predictor - Macro Indicators Collector
Thu thập các chỉ số macro ảnh hưởng giá vàng từ yfinance.

Macro indicators:
- DXY (Dollar Index) - tương quan nghịch với vàng
- USD/VND - ảnh hưởng giá vàng Việt Nam
- Oil WTI - indicator lạm phát
- US 10Y Treasury - opportunity cost of gold
- S&P 500 - risk appetite

Điểm mở rộng tương lai:
- Thêm VN-Index từ vnstock
- Thêm CPI data từ FRED API
- Thêm Fed Funds Rate
"""

from datetime import date, timedelta
from typing import Optional

import pandas as pd
import yfinance as yf
from sqlalchemy.orm import Session

from app.services.data_collector.base_collector import BaseCollector
from app.db.models import MacroIndicator
from app.db.database import get_session_factory
from app.utils.constants import ALL_YFINANCE_TICKERS
from app.utils.logger import get_logger

logger = get_logger(__name__)


class MacroCollector(BaseCollector):
    """Thu thập macro indicators từ yfinance."""

    def __init__(self):
        super().__init__("macro")
        # Bỏ xau_usd vì đã có collector riêng
        self.tickers = {
            k: v for k, v in ALL_YFINANCE_TICKERS.items()
            if k != "xau_usd"
        }

    def fetch_data(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> pd.DataFrame:
        """
        Fetch tất cả macro indicators từ yfinance.
        Returns DataFrame gộp tất cả indicators.
        """
        all_data = []

        for indicator_name, ticker_symbol in self.tickers.items():
            try:
                df = self._fetch_single_indicator(
                    indicator_name, ticker_symbol, start_date, end_date
                )
                if df is not None and not df.empty:
                    all_data.append(df)
            except Exception as e:
                self.logger.error(
                    f"Lỗi fetch {indicator_name} ({ticker_symbol}): {e}"
                )
                continue

        if not all_data:
            return pd.DataFrame()

        result = pd.concat(all_data, ignore_index=True)
        self.logger.info(f"Tổng cộng fetch được {len(result)} macro records")
        return result

    def _fetch_single_indicator(
        self,
        indicator_name: str,
        ticker_symbol: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> pd.DataFrame:
        """Fetch 1 indicator từ yfinance."""

        # Xác định start_date (incremental)
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
            self.logger.info(f"{indicator_name}: đã cập nhật")
            return pd.DataFrame()

        self.logger.info(
            f"Fetching {indicator_name} ({ticker_symbol}): "
            f"{start_date} → {end_date}"
        )

        ticker = yf.Ticker(ticker_symbol)
        df = ticker.history(
            start=start_date.isoformat(),
            end=(end_date + timedelta(days=1)).isoformat(),
            interval="1d",
        )

        if df.empty:
            self.logger.warning(f"{indicator_name}: không có dữ liệu")
            return pd.DataFrame()

        # Chuẩn hóa
        df = df.reset_index()
        df = df.rename(columns={
            "Date": "date",
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume",
        })

        keep_cols = ["date", "open", "high", "low", "close", "volume"]
        df = df[[c for c in keep_cols if c in df.columns]]
        df["date"] = pd.to_datetime(df["date"]).dt.date
        df["indicator"] = indicator_name

        self.logger.info(f"{indicator_name}: {len(df)} records")
        return df

    def store_data(self, df: pd.DataFrame, db: Session) -> int:
        """Lưu macro data vào bảng macro_indicators."""
        if df.empty:
            return 0

        count = 0
        for _, row in df.iterrows():
            existing = db.query(MacroIndicator).filter_by(
                date=row["date"],
                indicator=row["indicator"]
            ).first()

            if existing:
                existing.open = row.get("open")
                existing.high = row.get("high")
                existing.low = row.get("low")
                existing.close = row["close"]
                existing.volume = row.get("volume")
            else:
                record = MacroIndicator(
                    date=row["date"],
                    indicator=row["indicator"],
                    open=row.get("open"),
                    high=row.get("high"),
                    low=row.get("low"),
                    close=row["close"],
                    volume=row.get("volume"),
                )
                db.add(record)
                count += 1

        return count
