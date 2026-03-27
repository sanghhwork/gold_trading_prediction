"""
Gold Predictor - SJC Collector (V2 - Resilient)
Thu thập giá vàng Việt Nam từ nhiều nguồn với fallback chain.

Chain: sjc.com.vn → giavang.net → vang.today → empty

Nguồn:
1. sjc.com.vn - API chính thức (primary)
2. giavang.net - Tổng hợp nhiều đơn vị (fallback 1)
3. vang.today - API giá vàng miễn phí (fallback 2)

Điểm mở rộng tương lai:
- Thêm nguồn DOJI, PNJ, Bảo Tín Minh Châu
- Thêm lịch sử giá SJC từ giavang.net
- Thêm so sánh giá giữa các đơn vị
"""

from datetime import date, datetime
from typing import Optional

import pandas as pd
from sqlalchemy.orm import Session

from app.services.data_collector.base_collector import BaseCollector
from app.db.models import GoldPrice
from app.utils.logger import get_logger

logger = get_logger(__name__)


class SJCCollector(BaseCollector):
    """Thu thập giá vàng SJC với fallback chain."""

    def __init__(self):
        super().__init__("sjc")

    def fetch_data(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> pd.DataFrame:
        """
        Fetch giá SJC với fallback chain.
        Chain: sjc.com.vn → giavang.net → vang.today → empty
        """
        # Nguồn 1: sjc.com.vn API (primary)
        result = self._fetch_sjc_api()

        # Nguồn 2: giavang.net API (fallback 1)
        if result is None:
            self.logger.info("[FALLBACK] SJC: sjc.com.vn failed → thử giavang.net...")
            result = self._fetch_giavang_net()

        # Nguồn 3: vang.today API (fallback 2)
        if result is None:
            self.logger.info("[FALLBACK] SJC: giavang.net failed → thử vang.today...")
            result = self._fetch_vang_today()

        if result is None:
            self.logger.warning("[FALLBACK] SJC: Tất cả nguồn đều fail")
            return pd.DataFrame()

        df = pd.DataFrame([result])
        self.logger.info(
            f"SJC giá hôm nay: Mua={result['buy_price']:,.0f} | "
            f"Bán={result['sell_price']:,.0f} VND/lượng"
        )
        return df

    def _fetch_sjc_api(self) -> Optional[dict]:
        """
        Fetch từ sjc.com.vn internal API.
        Endpoint: POST /GoldPrice/Services/PriceService.ashx
        """
        url = "https://sjc.com.vn/GoldPrice/Services/PriceService.ashx"

        try:
            session = self._get_session()
            response = session.post(
                url,
                data={
                    "method": "GetCurrentGoldPricesByBranch",
                    "BranchId": "1",
                },
                headers={
                    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                    "X-Requested-With": "XMLHttpRequest",
                    "Referer": "https://sjc.com.vn/gia-vang-online",
                },
                timeout=15,
            )
            response.raise_for_status()
            data = response.json()

            if not data.get("success") or not data.get("data"):
                self.logger.warning(f"sjc.com.vn API response không hợp lệ")
                return None

            # Tìm "Vàng SJC 1L, 10L, 1KG" (giá chuẩn)
            for item in data["data"]:
                type_name = item.get("TypeName", "")
                if "1L" in type_name and "10L" in type_name:
                    buy = item.get("BuyValue", 0)
                    sell = item.get("SellValue", 0)

                    if buy > 0 and sell > 0:
                        self.logger.info(f"sjc.com.vn: {type_name} - Mua={buy:,.0f}, Bán={sell:,.0f}")
                        return {
                            "date": date.today(),
                            "source": "sjc",
                            "open": None, "high": None, "low": None,
                            "close": sell,
                            "volume": None,
                            "buy_price": buy,
                            "sell_price": sell,
                        }

            # Fallback: lấy dòng đầu tiên
            first = data["data"][0]
            buy = first.get("BuyValue", 0)
            sell = first.get("SellValue", 0)
            if buy > 0 and sell > 0:
                self.logger.info(f"sjc.com.vn (fallback): {first.get('TypeName')} - Mua={buy:,.0f}, Bán={sell:,.0f}")
                return {
                    "date": date.today(),
                    "source": "sjc",
                    "open": None, "high": None, "low": None,
                    "close": sell,
                    "volume": None,
                    "buy_price": buy,
                    "sell_price": sell,
                }

            self.logger.warning("sjc.com.vn: Không tìm thấy giá SJC 1L trong response")
            return None

        except Exception as e:
            self.logger.error(f"sjc.com.vn API error: {e}")
            return None

    def _fetch_giavang_net(self) -> Optional[dict]:
        """
        Fetch từ giavang.net API.
        Endpoint: GET https://api2.giavang.net/v1/gold/last-price
        """
        url = "https://api2.giavang.net/v1/gold/last-price"
        params = {
            "codes[]": ["SJL1L10"],
        }

        try:
            session = self._get_session()
            response = session.get(
                url,
                params=params,
                headers={
                    "Referer": "https://giavang.net/bang-gia-vang-trong-nuoc/",
                },
                timeout=15,
            )
            response.raise_for_status()
            data = response.json()

            # Parse giavang.net response
            if isinstance(data, list) and len(data) > 0:
                item = data[0]
                buy = item.get("buy", 0)
                sell = item.get("sell", 0)

                if buy > 0 and sell > 0:
                    self.logger.info(f"giavang.net: SJC - Mua={buy:,.0f}, Bán={sell:,.0f}")
                    return {
                        "date": date.today(),
                        "source": "sjc",
                        "open": None, "high": None, "low": None,
                        "close": sell,
                        "volume": None,
                        "buy_price": buy,
                        "sell_price": sell,
                    }
            elif isinstance(data, dict):
                for key, item in data.items():
                    if isinstance(item, dict):
                        buy = item.get("buy", item.get("Buy", 0))
                        sell = item.get("sell", item.get("Sell", 0))
                        if buy > 0 and sell > 0:
                            self.logger.info(f"giavang.net: {key} - Mua={buy:,.0f}, Bán={sell:,.0f}")
                            return {
                                "date": date.today(),
                                "source": "sjc",
                                "open": None, "high": None, "low": None,
                                "close": sell,
                                "volume": None,
                                "buy_price": buy,
                                "sell_price": sell,
                            }

            self.logger.warning(f"giavang.net: Response format không khớp: {str(data)[:200]}")
            return None

        except Exception as e:
            self.logger.error(f"giavang.net API error: {e}")
            return None

    def _fetch_vang_today(self) -> Optional[dict]:
        """
        Fetch từ vang.today API (fallback cuối).
        Endpoint: GET https://vang.today/prices.php?type=SJL1L10
        
        Response: {"success": true, "prices": {"SJL1L10": {"buy": ..., "sell": ...}}}
        Miễn phí, không cần key, cập nhật 5 phút, CORS enabled.
        """
        try:
            from app.utils.constants import VANG_TODAY_API_URL
        except ImportError:
            VANG_TODAY_API_URL = "https://vang.today/prices.php"

        try:
            session = self._get_session()
            response = session.get(
                VANG_TODAY_API_URL,
                params={"type": "SJL1L10"},
                headers={
                    "Referer": "https://vang.today/",
                },
                timeout=15,
            )
            response.raise_for_status()
            data = response.json()

            if not data.get("success"):
                self.logger.warning(f"vang.today: response không thành công")
                return None

            prices = data.get("prices", {})
            sjc_data = prices.get("SJL1L10", {})
            
            buy = sjc_data.get("buy", 0)
            sell = sjc_data.get("sell", 0)

            if buy > 0 and sell > 0:
                self.logger.info(f"vang.today: SJC - Mua={buy:,.0f}, Bán={sell:,.0f}")
                return {
                    "date": date.today(),
                    "source": "sjc",
                    "open": None, "high": None, "low": None,
                    "close": sell,
                    "volume": None,
                    "buy_price": buy,
                    "sell_price": sell,
                }

            self.logger.warning("vang.today: Không có giá SJC hợp lệ")
            return None

        except Exception as e:
            self.logger.error(f"vang.today API error: {e}")
            return None

    def validate_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validate giá SJC."""
        if df.empty:
            return df

        # Giá SJC hợp lệ: > 50 triệu VND/lượng
        valid = df[
            (df["buy_price"] > 50_000_000) &
            (df["sell_price"] > 50_000_000) &
            (df["sell_price"] > df["buy_price"])
        ]

        if len(valid) < len(df):
            self.logger.warning(f"Loại bỏ {len(df) - len(valid)} records SJC không hợp lệ")

        return valid

    def store_data(self, df: pd.DataFrame, db) -> int:
        """Lưu giá SJC vào bảng gold_prices (upsert by date)."""
        if df.empty:
            return 0

        count = 0
        for _, row in df.iterrows():
            existing = db.query(GoldPrice).filter(
                GoldPrice.date == row["date"],
                GoldPrice.source == "sjc",
            ).first()

            if existing:
                existing.buy_price = row["buy_price"]
                existing.sell_price = row["sell_price"]
                existing.close = row["sell_price"]
                existing.updated_at = datetime.now()
                self.logger.info(f"SJC updated: {row['date']}")
            else:
                record = GoldPrice(
                    date=row["date"],
                    source="sjc",
                    close=row["sell_price"],
                    buy_price=row["buy_price"],
                    sell_price=row["sell_price"],
                )
                db.add(record)
                count += 1

        return count
