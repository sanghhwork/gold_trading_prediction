"""
Gold Predictor - XAU/USD Collector (V2 - Resilient)
Thu thập giá vàng XAU/USD với fallback chain.

Chain: yfinance → Alpha Vantage → raise error

Nguồn:
1. yfinance (Yahoo Finance, ticker: GC=F) - Primary
2. Alpha Vantage (free API, 25 calls/ngày) - Fallback

Điểm mở rộng tương lai:
- Thêm Twelve Data hoặc Stooq làm fallback thứ 3
- Thêm Polygon.io khi có budget
"""

import time
from datetime import date, timedelta
from typing import Optional

import pandas as pd
import yfinance as yf
from sqlalchemy.orm import Session

from app.services.data_collector.base_collector import BaseCollector
from app.db.models import GoldPrice
from app.db.database import get_session_factory
from app.utils.constants import TICKER_XAU_USD
from app.utils.logger import get_logger

logger = get_logger(__name__)


class XAUCollector(BaseCollector):
    """Thu thập giá vàng XAU/USD với fallback chain."""

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
        Fetch XAU/USD OHLCV data với fallback chain.
        Chain: yfinance → Alpha Vantage → raise error
        """
        # Xác định khoảng thời gian cần fetch
        if start_date is None:
            SessionLocal = get_session_factory()
            db = SessionLocal()
            try:
                last_date = self.get_last_date_in_db(
                    db, GoldPrice, {"source": self.source}
                )
            finally:
                db.close()

            if last_date:
                start_date = last_date + timedelta(days=1)
                self.logger.info(f"Incremental fetch từ {start_date}")
            else:
                start_date = date.today() - timedelta(days=365 * 5)
                self.logger.info(f"Full fetch từ {start_date}")

        if end_date is None:
            end_date = date.today()

        if start_date >= end_date:
            self.logger.info("Dữ liệu đã cập nhật, không cần fetch mới")
            return pd.DataFrame()

        # Source 1: yfinance (primary)
        df = self._fetch_yfinance(start_date, end_date)
        if df is not None and not df.empty:
            return df

        # Source 2: Alpha Vantage (fallback)
        self.logger.info("[FALLBACK] XAU: yfinance failed → thử Alpha Vantage")
        df = self._fetch_alpha_vantage(start_date, end_date)
        if df is not None and not df.empty:
            self.logger.info("[FALLBACK] XAU: Alpha Vantage thành công")
            return df

        self.logger.error("[FALLBACK] XAU: Tất cả nguồn đều fail")
        return pd.DataFrame()

    def _fetch_yfinance(self, start_date: date, end_date: date) -> Optional[pd.DataFrame]:
        """Fetch XAU/USD từ yfinance (primary source)."""
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
                return None

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

            keep_cols = ["date", "open", "high", "low", "close", "volume"]
            df = df[[c for c in keep_cols if c in df.columns]]
            df["date"] = pd.to_datetime(df["date"]).dt.date
            df["source"] = self.source

            self.logger.info(f"Đã fetch {len(df)} records XAU/USD từ yfinance")
            return df

        except Exception as e:
            self.logger.error(f"Lỗi fetch XAU/USD từ yfinance: {e}")
            return None

    def _fetch_alpha_vantage(self, start_date: date, end_date: date) -> Optional[pd.DataFrame]:
        """
        Fetch XAU/USD từ Alpha Vantage API (fallback).
        
        Rate limit: 5 calls/phút, 25 calls/ngày (free tier)
        → Sleep 15s trước khi gọi để tránh xung đột với macro_collector
        """
        try:
            from app.config import get_settings
            settings = get_settings()
            api_key = getattr(settings, 'alpha_vantage_api_key', None)
            call_delay = getattr(settings, 'alpha_vantage_call_delay', 15.0)
        except Exception:
            import os
            api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
            call_delay = 15.0

        if not api_key:
            self.logger.warning(
                "[FALLBACK] XAU Alpha Vantage: API key chưa cấu hình "
                "(ALPHA_VANTAGE_API_KEY)"
            )
            return None

        self.logger.info(f"Đang fetch XAU/USD từ Alpha Vantage...")
        
        # Rate limit delay
        self.logger.info(f"[RATE_LIMIT] Đợi {call_delay}s trước Alpha Vantage call...")
        time.sleep(call_delay)

        try:
            session = self._get_session()
            
            # Alpha Vantage: TIME_SERIES_DAILY cho GLD ETF (proxy cho gold price)
            # hoặc dùng CURRENCY_EXCHANGE_RATE cho XAU/USD
            response = session.get(
                "https://www.alphavantage.co/query",
                params={
                    "function": "TIME_SERIES_DAILY",
                    "symbol": "GLD",
                    "outputsize": "full" if (end_date - start_date).days > 100 else "compact",
                    "apikey": api_key,
                },
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()

            # Check API error
            if "Error Message" in data or "Note" in data:
                error_msg = data.get("Error Message", data.get("Note", "Unknown"))
                self.logger.error(f"Alpha Vantage API error: {error_msg}")
                return None

            time_series = data.get("Time Series (Daily)", {})
            if not time_series:
                self.logger.warning("Alpha Vantage: Không có dữ liệu Time Series")
                return None

            records = []
            for date_str, values in time_series.items():
                try:
                    d = date.fromisoformat(date_str)
                    if start_date <= d <= end_date:
                        records.append({
                            "date": d,
                            "open": float(values.get("1. open", 0)),
                            "high": float(values.get("2. high", 0)),
                            "low": float(values.get("3. low", 0)),
                            "close": float(values.get("4. close", 0)),
                            "volume": float(values.get("5. volume", 0)),
                            "source": self.source,
                        })
                except (ValueError, KeyError) as e:
                    self.logger.warning(f"Lỗi parse Alpha Vantage record: {e}")
                    continue

            if not records:
                self.logger.warning("Alpha Vantage: Không có records trong khoảng thời gian yêu cầu")
                return None

            df = pd.DataFrame(records)
            df = df.sort_values("date").reset_index(drop=True)
            self.logger.info(f"Alpha Vantage: {len(df)} records XAU/USD (via GLD ETF)")
            return df

        except Exception as e:
            self.logger.error(f"Lỗi fetch XAU/USD từ Alpha Vantage: {e}")
            return None

    def store_data(self, df: pd.DataFrame, db: Session) -> int:
        """
        Lưu XAU/USD data vào bảng gold_prices.
        Sử dụng upsert (insert or update) để tránh duplicate.
        """
        if df.empty:
            return 0

        count = 0
        for _, row in df.iterrows():
            existing = db.query(GoldPrice).filter_by(
                date=row["date"],
                source=row["source"]
            ).first()

            if existing:
                existing.open = row.get("open")
                existing.high = row.get("high")
                existing.low = row.get("low")
                existing.close = row["close"]
                existing.volume = row.get("volume")
            else:
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
