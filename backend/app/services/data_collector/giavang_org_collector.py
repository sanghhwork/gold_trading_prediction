"""
Gold Predictor - Giavang.org Collector (V2 - Resilient)
Thu thập giá vàng SJC/PNJ/DOJI từ giavang.org.

Dùng ResilientSession với UA rotation, retry logic.
Delay crawl lịch sử: 2-3s (random) giữa các requests.

Nguồn dữ liệu:
- Trang chính: https://giavang.org/ (giá realtime nhiều đơn vị)
- Lịch sử: https://giavang.org/trong-nuoc/sjc/lich-su/YYYY-MM-DD.html

Đặc điểm:
- Parse HTML (BeautifulSoup), không có API JSON
- Nhiều khu vực: HCM, Hà Nội, Đà Nẵng, Hạ Long...
- Nhiều đơn vị: SJC, PNJ, DOJI, Mi Hồng, Ngọc Thẩm...
- Đơn vị giá: x1000 VND/lượng (163.000 = 163,000,000 VND)
- Lịch sử từ 07/2009 đến hiện tại

Điểm mở rộng tương lai:
- Crawl full lịch sử SJC (2009-now) cho training data
- So sánh giá giữa các đơn vị (arbitrage detection)
- Theo dõi spread mua-bán theo thời gian
"""

import random
import re
import time
from datetime import date, datetime, timedelta
from typing import Optional

import pandas as pd
from bs4 import BeautifulSoup

from app.services.data_collector.base_collector import BaseCollector
from app.db.models import GoldPrice
from app.utils.logger import get_logger

logger = get_logger(__name__)

# URL patterns
BASE_URL = "https://giavang.org"
HISTORY_URL = f"{BASE_URL}/trong-nuoc/sjc/lich-su"


class GiavangOrgCollector(BaseCollector):
    """Thu thập giá vàng từ giavang.org (nhiều đơn vị, nhiều khu vực)."""

    def __init__(self):
        super().__init__("giavang_org")

    def fetch_data(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> pd.DataFrame:
        """
        Fetch giá từ giavang.org.
        - Nếu không có start_date: lấy giá hôm nay từ trang chính
        - Nếu có start_date: crawl lịch sử từ start_date đến end_date
        """
        if start_date:
            return self._fetch_historical(start_date, end_date or date.today())
        else:
            return self._fetch_today()

    def _fetch_today(self) -> pd.DataFrame:
        """Fetch giá hôm nay từ trang chính giavang.org."""
        self.logger.info("Fetching giavang.org trang chinh...")

        try:
            session = self._get_session()
            
            # Referer chain: truy cập trang chính trước
            response = session.get(
                BASE_URL,
                headers={"Referer": "https://www.google.com/"},
                timeout=15,
            )
            response.raise_for_status()
            response.encoding = "utf-8"

            soup = BeautifulSoup(response.text, "html.parser")
            tables = soup.find_all("table")

            if not tables:
                self.logger.warning("giavang.org: Khong tim thay bang gia")
                return pd.DataFrame()

            # Parse table đầu tiên (bảng giá chính)
            records = self._parse_price_table(tables[0], date.today())

            if records:
                df = pd.DataFrame(records)
                self.logger.info(
                    f"giavang.org: {len(records)} records "
                    f"({len(set(r['organization'] for r in records))} don vi)"
                )
                return df

            self.logger.warning("giavang.org: Khong parse duoc du lieu gia")
            return pd.DataFrame()

        except Exception as e:
            self.logger.error(f"giavang.org fetch error: {e}")
            return pd.DataFrame()

    def _fetch_historical(self, start: date, end: date) -> pd.DataFrame:
        """Crawl giá lịch sử từ giavang.org/trong-nuoc/sjc/lich-su/."""
        self.logger.info(f"Crawling giavang.org lich su: {start} -> {end}")

        all_records = []
        current = start
        error_count = 0

        while current <= end:
            # Skip weekends (thường không có giá)
            if current.weekday() >= 5:  # Sat/Sun
                current += timedelta(days=1)
                continue

            url = f"{HISTORY_URL}/{current.strftime('%Y-%m-%d')}.html"

            try:
                session = self._get_session()
                response = session.get(
                    url,
                    headers={"Referer": BASE_URL},
                    timeout=10,
                )
                if response.status_code == 200:
                    response.encoding = "utf-8"
                    soup = BeautifulSoup(response.text, "html.parser")
                    tables = soup.find_all("table")

                    if tables:
                        records = self._parse_price_table(tables[0], current)
                        if records:
                            all_records.extend(records)
                            error_count = 0  # Reset error counter

                elif response.status_code == 404:
                    pass  # Ngày không có dữ liệu, skip
                else:
                    self.logger.warning(f"  {current}: HTTP {response.status_code}")

            except Exception as e:
                error_count += 1
                self.logger.warning(f"  {current}: Error - {e}")
                if error_count > 5:
                    self.logger.error("Qua nhieu loi lien tiep, dung crawl.")
                    break

            current += timedelta(days=1)

            # Rate limit: 2-3s random delay (tăng từ 0.5s để tránh bị block)
            time.sleep(random.uniform(2.0, 3.0))

        if all_records:
            df = pd.DataFrame(all_records)
            self.logger.info(f"giavang.org lich su: {len(df)} records, {df['date'].nunique()} ngay")
            return df

        return pd.DataFrame()

    def _parse_price_table(self, table, price_date: date) -> list[dict]:
        """
        Parse bảng giá từ giavang.org HTML table.

        Format bảng:
        | Khu vực | Hệ thống | Mua vào | Bán ra |
        | TP. HCM | SJC      | 163.000 | 166.000 |
        |         | PNJ      | 163.000 | 166.000 |
        """
        records = []
        rows = table.find_all("tr")
        current_region = ""

        for row in rows:
            cells = row.find_all(["td", "th"])
            cell_texts = [c.get_text(strip=True) for c in cells]

            if not cell_texts or len(cell_texts) < 3:
                continue

            # Skip header row
            if any(h in cell_texts[0].lower() for h in ["khu", "hệ", "mua", "bán"]):
                continue

            # Parse row - format varies
            if len(cell_texts) >= 4:
                # Full row: [khu_vuc, he_thong, mua, ban]
                current_region = cell_texts[0] or current_region
                org = cell_texts[1]
                buy_str = cell_texts[2]
                sell_str = cell_texts[3]
            elif len(cell_texts) == 3:
                # Short row: [he_thong, mua, ban] (khu vực từ row trước)
                org = cell_texts[0]
                buy_str = cell_texts[1]
                sell_str = cell_texts[2]
            else:
                continue

            # Parse giá (format: "163.000" = 163,000 x 1000 = 163,000,000 VND)
            buy = self._parse_price(buy_str)
            sell = self._parse_price(sell_str)

            if buy and sell and buy > 0 and sell > 0:
                records.append({
                    "date": price_date,
                    "source": "giavang_org",
                    "organization": org.strip(),
                    "region": current_region.strip(),
                    "buy_price": buy,
                    "sell_price": sell,
                    "close": sell,  # Giá bán làm giá tham chiếu
                    "open": None,
                    "high": None,
                    "low": None,
                    "volume": None,
                })

        return records

    @staticmethod
    def _parse_price(price_str: str) -> Optional[float]:
        """
        Parse giá từ string sang float (VND).
        "163.000" → 163,000,000
        "162.800" → 162,800,000
        """
        if not price_str:
            return None

        # Loại bỏ ký tự không phải số và dấu chấm
        cleaned = re.sub(r"[^\d.]", "", price_str.strip())
        if not cleaned:
            return None

        try:
            # Giá trên giavang.org có format "163.000" (x1000 VND)
            # Nếu có format 6 chữ số tổng (vd: 163000 hoặc 163.000)
            if "." in cleaned:
                parts = cleaned.split(".")
                # "163.000" → 163000 × 1000 = 163,000,000
                number = int(parts[0]) * 1000 + int(parts[1]) if len(parts) == 2 else float(cleaned)
                return number * 1000
            else:
                number = float(cleaned)
                # Nếu số > 100000 → đã là VND đầy đủ
                if number > 100_000:
                    return number
                # Nếu < 1000 → đơn vị x1000
                return number * 1_000_000
        except (ValueError, IndexError):
            return None

    def validate_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validate giá vàng từ giavang.org."""
        if df.empty:
            return df

        # Giá hợp lệ: > 50 triệu VND/lượng
        valid = df[
            (df["buy_price"] > 50_000_000) &
            (df["sell_price"] > 50_000_000) &
            (df["sell_price"] >= df["buy_price"])
        ]

        if len(valid) < len(df):
            dropped = len(df) - len(valid)
            self.logger.warning(f"Loai bo {dropped}/{len(df)} records khong hop le")

        return valid

    def store_data(self, df: pd.DataFrame, db) -> int:
        """
        Lưu giá vào DB.
        Chỉ lưu giá SJC HCM làm tham chiếu chính (để so sánh với sjc.com.vn).
        """
        if df.empty:
            return 0

        # Lọc SJC chính (ưu tiên SJC HCM)
        sjc_df = df[df["organization"].str.upper().str.contains("SJC", na=False)]
        if sjc_df.empty:
            sjc_df = df.head(1)  # Fallback lấy dòng đầu

        count = 0
        for _, row in sjc_df.iterrows():
            # Check trùng ngày+source
            existing = db.query(GoldPrice).filter(
                GoldPrice.date == row["date"],
                GoldPrice.source == "giavang_org",
            ).first()

            if existing:
                existing.buy_price = row["buy_price"]
                existing.sell_price = row["sell_price"]
                existing.close = row["sell_price"]
                existing.updated_at = datetime.now()
            else:
                record = GoldPrice(
                    date=row["date"],
                    source="giavang_org",
                    close=row["sell_price"],
                    buy_price=row["buy_price"],
                    sell_price=row["sell_price"],
                )
                db.add(record)
                count += 1

            # Chỉ lưu 1 record SJC mỗi ngày
            break

        return count

    def fetch_multi_org_prices(self) -> pd.DataFrame:
        """
        Lấy giá tất cả đơn vị (SJC, PNJ, DOJI, ...) cho so sánh.
        Trả về DataFrame đầy đủ không lọc.
        """
        df = self._fetch_today()
        if df.empty:
            return df
        return self.validate_data(df)
