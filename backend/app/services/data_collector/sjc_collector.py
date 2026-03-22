"""
Gold Predictor - SJC Collector (Fixed)
Thu thập giá vàng Việt Nam từ nhiều nguồn.

Nguồn:
1. sjc.com.vn - API chính thức (primary)
   POST /GoldPrice/Services/PriceService.ashx
   → JSON response với BuyValue, SellValue

2. giavang.net - Tổng hợp nhiều đơn vị (fallback)
   GET https://api2.giavang.net/v1/gold/last-price?codes[]=SJL1L10
   → JSON response

Điểm mở rộng tương lai:
- Thêm nguồn DOJI, PNJ, Bảo Tín Minh Châu
- Thêm lịch sử giá SJC từ giavang.net
- Thêm so sánh giá giữa các đơn vị
"""

from datetime import date, datetime
from typing import Optional

import pandas as pd
import requests

from app.services.data_collector.base_collector import BaseCollector
from app.db.models import GoldPrice
from app.utils.logger import get_logger

logger = get_logger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}


class SJCCollector(BaseCollector):
    """Thu thập giá vàng SJC từ sjc.com.vn + giavang.net."""

    def __init__(self):
        super().__init__("sjc")

    def fetch_data(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> pd.DataFrame:
        """Fetch giá SJC từ API, fallback giữa các nguồn."""

        # Nguồn 1: sjc.com.vn API (primary)
        result = self._fetch_sjc_api()

        # Nguồn 2: giavang.net API (fallback)
        if result is None:
            self.logger.info("sjc.com.vn failed, fallback sang giavang.net...")
            result = self._fetch_giavang_net()

        if result is None:
            self.logger.warning("Không thể lấy giá SJC từ bất kỳ nguồn nào")
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
            response = requests.post(
                url,
                data={
                    "method": "GetCurrentGoldPricesByBranch",
                    "BranchId": "1",
                },
                headers={
                    **HEADERS,
                    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                    "X-Requested-With": "XMLHttpRequest",
                    "Referer": "https://sjc.com.vn/gia-vang-online",
                },
                timeout=15,
            )
            response.raise_for_status()
            data = response.json()

            if not data.get("success") or not data.get("data"):
                self.logger.warning(f"sjc.com.vn API response không hợp lệ: {data}")
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
                            "open": None,
                            "high": None,
                            "low": None,
                            "close": sell,  # Giá bán SJC là giá tham chiếu
                            "volume": None,
                            "buy_price": buy,
                            "sell_price": sell,
                        }

            # Fallback: lấy dòng đầu tiên nếu không tìm thấy 1L
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

        except requests.RequestException as e:
            self.logger.error(f"sjc.com.vn API error: {e}")
            return None
        except (ValueError, KeyError) as e:
            self.logger.error(f"sjc.com.vn parse error: {e}")
            return None

    def _fetch_giavang_net(self) -> Optional[dict]:
        """
        Fetch từ giavang.net API.
        Endpoint: GET https://api2.giavang.net/v1/gold/last-price
        """
        url = "https://api2.giavang.net/v1/gold/last-price"
        params = {
            "codes[]": ["SJL1L10"],  # SJC 1 lượng, 10 lượng
        }

        try:
            response = requests.get(
                url,
                params=params,
                headers={
                    **HEADERS,
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
                # Thử parse format khác
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

        except requests.RequestException as e:
            self.logger.error(f"giavang.net API error: {e}")
            return None
        except (ValueError, KeyError) as e:
            self.logger.error(f"giavang.net parse error: {e}")
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
                # Update giá mới
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
