"""
Gold Predictor - Macro Indicators Collector (V2 - Resilient)
Thu thập các chỉ số macro ảnh hưởng giá vàng.

Chain: yfinance → Alpha Vantage (nếu có key) → skip indicator

Macro indicators:
- DXY (Dollar Index) - tương quan nghịch với vàng
- USD/VND - ảnh hưởng giá vàng Việt Nam
- Oil WTI - indicator lạm phát
- US 10Y Treasury - opportunity cost of gold
- S&P 500 - risk appetite
- GLD ETF - gold flows proxy

Điểm mở rộng tương lai:
- Thêm VN-Index từ vnstock
- Thêm CPI data từ FRED API
- Thêm Fed Funds Rate
- Thêm Twelve Data fallback
"""

import time
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

# Mapping indicator → Alpha Vantage config
# Dùng khi yfinance fail, mỗi indicator có function/symbol riêng
# Dễ thêm/bớt: chỉ cần thêm entry vào dict
ALPHA_VANTAGE_MAPPING = {
    "dxy": {
        "function": "TIME_SERIES_DAILY",
        "symbol": "UUP",  # UUP ETF proxy cho DXY
    },
    "usd_vnd": {
        "function": "CURRENCY_EXCHANGE_RATE",
        "from_currency": "USD",
        "to_currency": "VND",
    },
    "oil_wti": {
        "function": "WTI",  # Commodities endpoint
    },
    "sp500": {
        "function": "TIME_SERIES_DAILY",
        "symbol": "SPY",  # SPY ETF proxy cho S&P 500
    },
    "gld_etf": {
        "function": "TIME_SERIES_DAILY",
        "symbol": "GLD",
    },
    # us_10y: dùng FRED API thay vì Alpha Vantage (chính xác hơn)
}


class MacroCollector(BaseCollector):
    """Thu thập macro indicators với fallback chain."""

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
        Fetch tất cả macro indicators.
        Mỗi indicator: yfinance → Alpha Vantage → skip (log warning)
        """
        all_data = []

        for indicator_name, ticker_symbol in self.tickers.items():
            try:
                # Source 1: yfinance (primary)
                df = self._fetch_single_indicator(
                    indicator_name, ticker_symbol, start_date, end_date
                )
                
                if df is not None and not df.empty:
                    all_data.append(df)
                    continue
                
                # Source 2: Alpha Vantage (fallback)
                if indicator_name in ALPHA_VANTAGE_MAPPING:
                    self.logger.info(
                        f"[FALLBACK] {indicator_name}: yfinance failed → thử Alpha Vantage"
                    )
                    df = self._fetch_alpha_vantage_indicator(
                        indicator_name, start_date, end_date
                    )
                    if df is not None and not df.empty:
                        all_data.append(df)
                        self.logger.info(
                            f"[FALLBACK] {indicator_name}: Alpha Vantage thành công"
                        )
                        continue
                
                self.logger.warning(
                    f"[SKIP] {indicator_name}: Tất cả nguồn fail, bỏ qua"
                )
                
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
    ) -> Optional[pd.DataFrame]:
        """Fetch 1 indicator từ yfinance (primary source)."""

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

        try:
            ticker = yf.Ticker(ticker_symbol)
            df = ticker.history(
                start=start_date.isoformat(),
                end=(end_date + timedelta(days=1)).isoformat(),
                interval="1d",
            )

            if df.empty:
                self.logger.warning(f"{indicator_name}: yfinance không có dữ liệu")
                return None

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

            self.logger.info(f"{indicator_name}: {len(df)} records (yfinance)")
            return df

        except Exception as e:
            self.logger.error(f"{indicator_name}: yfinance error - {e}")
            return None

    def _fetch_alpha_vantage_indicator(
        self,
        indicator_name: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Optional[pd.DataFrame]:
        """
        Fetch 1 indicator từ Alpha Vantage API (fallback).
        
        Rate limit: 5 calls/phút → sleep 15s giữa mỗi call
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
                f"[FALLBACK] {indicator_name}: Alpha Vantage API key chưa cấu hình"
            )
            return None

        config = ALPHA_VANTAGE_MAPPING.get(indicator_name)
        if not config:
            return None

        # Rate limit delay
        self.logger.info(f"[RATE_LIMIT] Đợi {call_delay}s trước Alpha Vantage call...")
        time.sleep(call_delay)

        try:
            session = self._get_session()
            
            # Currency Exchange Rate (USD/VND) - format khác
            if config.get("function") == "CURRENCY_EXCHANGE_RATE":
                return self._fetch_av_currency_rate(
                    session, api_key, config, indicator_name
                )
            
            # WTI Commodity endpoint
            if config.get("function") == "WTI":
                return self._fetch_av_commodity(
                    session, api_key, indicator_name, start_date, end_date
                )

            # TIME_SERIES_DAILY (default)
            if end_date is None:
                end_date = date.today()
            if start_date is None:
                start_date = date.today() - timedelta(days=365 * 5)

            response = session.get(
                "https://www.alphavantage.co/query",
                params={
                    "function": config["function"],
                    "symbol": config["symbol"],
                    "outputsize": "full" if (end_date - start_date).days > 100 else "compact",
                    "apikey": api_key,
                },
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()

            if "Error Message" in data or "Note" in data:
                error_msg = data.get("Error Message", data.get("Note", ""))
                self.logger.error(f"Alpha Vantage error ({indicator_name}): {error_msg}")
                return None

            time_series = data.get("Time Series (Daily)", {})
            if not time_series:
                self.logger.warning(f"Alpha Vantage {indicator_name}: không có dữ liệu")
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
                            "indicator": indicator_name,
                        })
                except (ValueError, KeyError) as e:
                    continue

            if not records:
                return None

            df = pd.DataFrame(records).sort_values("date").reset_index(drop=True)
            self.logger.info(f"Alpha Vantage {indicator_name}: {len(df)} records")
            return df

        except Exception as e:
            self.logger.error(f"Alpha Vantage {indicator_name} error: {e}")
            return None

    def _fetch_av_currency_rate(
        self, session, api_key: str, config: dict, indicator_name: str
    ) -> Optional[pd.DataFrame]:
        """Fetch tỷ giá từ Alpha Vantage Currency Exchange Rate."""
        try:
            response = session.get(
                "https://www.alphavantage.co/query",
                params={
                    "function": "CURRENCY_EXCHANGE_RATE",
                    "from_currency": config["from_currency"],
                    "to_currency": config["to_currency"],
                    "apikey": api_key,
                },
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()

            rate_data = data.get("Realtime Currency Exchange Rate", {})
            if not rate_data:
                self.logger.warning(f"Alpha Vantage {indicator_name}: không có exchange rate")
                return None

            rate = float(rate_data.get("5. Exchange Rate", 0))
            if rate <= 0:
                return None

            df = pd.DataFrame([{
                "date": date.today(),
                "indicator": indicator_name,
                "close": rate,
                "open": None, "high": None, "low": None, "volume": None,
            }])
            self.logger.info(f"Alpha Vantage {indicator_name}: rate = {rate:,.2f}")
            return df

        except Exception as e:
            self.logger.error(f"Alpha Vantage currency rate error: {e}")
            return None

    def _fetch_av_commodity(
        self, session, api_key: str, indicator_name: str,
        start_date: Optional[date] = None, end_date: Optional[date] = None,
    ) -> Optional[pd.DataFrame]:
        """Fetch WTI Oil price từ Alpha Vantage Commodities endpoint."""
        try:
            response = session.get(
                "https://www.alphavantage.co/query",
                params={
                    "function": "WTI",
                    "interval": "daily",
                    "apikey": api_key,
                },
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()

            if "data" not in data:
                self.logger.warning(f"Alpha Vantage WTI: không có data")
                return None

            if end_date is None:
                end_date = date.today()
            if start_date is None:
                start_date = date.today() - timedelta(days=365 * 5)

            records = []
            for item in data["data"]:
                try:
                    if item.get("value") == ".":
                        continue
                    d = date.fromisoformat(item["date"])
                    if start_date <= d <= end_date:
                        records.append({
                            "date": d,
                            "indicator": indicator_name,
                            "close": float(item["value"]),
                            "open": None, "high": None, "low": None, "volume": None,
                        })
                except (ValueError, KeyError):
                    continue

            if not records:
                return None

            df = pd.DataFrame(records).sort_values("date").reset_index(drop=True)
            self.logger.info(f"Alpha Vantage WTI: {len(df)} records")
            return df

        except Exception as e:
            self.logger.error(f"Alpha Vantage WTI error: {e}")
            return None

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
