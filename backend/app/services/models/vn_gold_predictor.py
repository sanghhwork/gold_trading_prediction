"""
Gold Predictor - VN Gold Predictor
Dự đoán giá vàng Việt Nam (SJC) từ giá thế giới.

Công thức cơ bản:
  SJC (VND/lượng) ≈ XAU/USD × USD/VND × 37.5 / 31.1035 + premium

Premium SJC thường dao động 5-20 triệu VND/lượng so với thế giới.

Điểm mở rộng tương lai:
- Thêm ML model riêng cho premium prediction
- Thêm DOJI, PNJ prediction
- Thêm historical premium analysis
"""

from datetime import date, datetime
from typing import Optional

import numpy as np
import pandas as pd

from app.db.database import get_session_factory
from app.db.models import GoldPrice, MacroIndicator
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Hệ số quy đổi
TROY_OUNCE_GRAMS = 31.1035  # 1 troy ounce = 31.1035 grams
LUONG_GRAMS = 37.5          # 1 lượng = 37.5 grams
LUONG_PER_OUNCE = LUONG_GRAMS / TROY_OUNCE_GRAMS  # ~1.2057


class VNGoldPredictor:
    """
    Dự đoán giá vàng Việt Nam từ XAU/USD + USD/VND.
    """

    def __init__(self):
        self.logger = get_logger("vn_gold_predictor")

    def predict_sjc_price(
        self,
        xau_usd_price: float,
        usd_vnd_rate: Optional[float] = None,
        premium_vnd: Optional[float] = None,
    ) -> dict:
        """
        Tính giá SJC quy đổi từ XAU/USD.

        Args:
            xau_usd_price: Giá XAU/USD (USD/oz)
            usd_vnd_rate: Tỷ giá USD/VND (nếu None → lấy từ DB)
            premium_vnd: Premium SJC (VND/lượng, nếu None → ước lượng)

        Returns:
            dict với giá SJC dự đoán (mua/bán), quy đổi, premium
        """
        # Lấy tỷ giá USD/VND
        if usd_vnd_rate is None:
            usd_vnd_rate = self._get_latest_usd_vnd()
            if usd_vnd_rate is None:
                usd_vnd_rate = 25_800  # Default fallback

        # Tính giá thế giới quy đổi VND/lượng
        world_price_vnd = xau_usd_price * usd_vnd_rate * LUONG_PER_OUNCE

        # Ước lượng premium SJC
        if premium_vnd is None:
            premium_vnd = self._estimate_premium()

        # Giá SJC dự đoán
        sjc_estimated = world_price_vnd + premium_vnd
        sjc_buy = sjc_estimated - 3_000_000   # Spread mua-bán ~3 triệu
        sjc_sell = sjc_estimated

        result = {
            "xau_usd": round(xau_usd_price, 2),
            "usd_vnd": round(usd_vnd_rate, 0),
            "world_price_vnd_per_luong": round(world_price_vnd, 0),
            "premium_vnd": round(premium_vnd, 0),
            "sjc_buy_estimated": round(sjc_buy, 0),
            "sjc_sell_estimated": round(sjc_sell, 0),
            "formula": f"XAU({xau_usd_price:.0f}) x VND({usd_vnd_rate:.0f}) x {LUONG_PER_OUNCE:.4f} + premium({premium_vnd/1e6:.1f}M)",
        }

        self.logger.info(
            f"VN Gold: ${xau_usd_price:.0f} × {usd_vnd_rate:.0f} VND "
            f"= {world_price_vnd/1e6:.1f}M + premium {premium_vnd/1e6:.1f}M "
            f"= {sjc_sell/1e6:.1f}M VND/luong"
        )

        return result

    def predict_from_xau_forecast(
        self,
        xau_predictions: dict,
        usd_vnd_rate: Optional[float] = None,
    ) -> dict:
        """
        Dự đoán giá SJC từ XAU/USD forecast (1d/7d/30d).

        Args:
            xau_predictions: dict từ ModelTrainer.predict() cho mỗi horizon

        Returns:
            dict giá SJC dự đoán cho mỗi horizon
        """
        results = {}

        for horizon, pred in xau_predictions.items():
            if isinstance(pred, dict) and "predicted_price" in pred:
                xau_price = pred["predicted_price"]
                sjc = self.predict_sjc_price(xau_price, usd_vnd_rate)
                results[horizon] = {
                    "xau_predicted": xau_price,
                    "sjc_buy_predicted": sjc["sjc_buy_estimated"],
                    "sjc_sell_predicted": sjc["sjc_sell_estimated"],
                    "world_price_vnd": sjc["world_price_vnd_per_luong"],
                    "premium": sjc["premium_vnd"],
                }

        return results

    def get_current_analysis(self) -> dict:
        """
        Phân tích giá vàng VN hiện tại: so sánh SJC thực tế vs quy đổi.
        """
        # Lấy giá XAU/USD mới nhất
        xau_latest = self._get_latest_xau()
        if xau_latest is None:
            return {"error": "Khong co du lieu XAU/USD"}

        # Lấy giá SJC thực tế
        sjc_latest = self._get_latest_sjc()

        # Tính giá quy đổi
        converted = self.predict_sjc_price(xau_latest["close"])

        result = {
            "xau_usd": {
                "date": str(xau_latest["date"]),
                "close": xau_latest["close"],
            },
            "sjc_converted": {
                "world_price_vnd": converted["world_price_vnd_per_luong"],
                "estimated_sell": converted["sjc_sell_estimated"],
                "formula": converted["formula"],
            },
        }

        if sjc_latest:
            actual_premium = sjc_latest["sell_price"] - converted["world_price_vnd_per_luong"]
            result["sjc_actual"] = {
                "date": str(sjc_latest["date"]),
                "buy": sjc_latest["buy_price"],
                "sell": sjc_latest["sell_price"],
            }
            result["premium_analysis"] = {
                "actual_premium": round(actual_premium, 0),
                "premium_pct": round(actual_premium / converted["world_price_vnd_per_luong"] * 100, 2),
                "note": "Premium > 10% la bat thuong, thuong 3-8%",
            }

        return result

    def _get_latest_usd_vnd(self) -> Optional[float]:
        """Lấy tỷ giá USD/VND mới nhất từ DB."""
        try:
            SessionLocal = get_session_factory()
            db = SessionLocal()
            record = db.query(MacroIndicator).filter_by(
                indicator="usd_vnd"
            ).order_by(MacroIndicator.date.desc()).first()
            db.close()
            return record.close if record else None
        except Exception as e:
            self.logger.warning(f"Khong lay duoc USD/VND: {e}")
            return None

    def _get_latest_xau(self) -> Optional[dict]:
        """Lấy giá XAU/USD mới nhất."""
        try:
            SessionLocal = get_session_factory()
            db = SessionLocal()
            record = db.query(GoldPrice).filter_by(
                source="xau_usd"
            ).order_by(GoldPrice.date.desc()).first()
            db.close()
            if record:
                return {"date": record.date, "close": record.close}
            return None
        except Exception:
            return None

    def _get_latest_sjc(self) -> Optional[dict]:
        """Lấy giá SJC thực tế mới nhất."""
        try:
            SessionLocal = get_session_factory()
            db = SessionLocal()
            record = db.query(GoldPrice).filter_by(
                source="sjc"
            ).order_by(GoldPrice.date.desc()).first()
            db.close()
            if record:
                return {
                    "date": record.date,
                    "buy_price": record.buy_price,
                    "sell_price": record.sell_price,
                }
            return None
        except Exception:
            return None

    def _estimate_premium(self) -> float:
        """
        Ước lượng premium SJC.
        Dựa trên lịch sử: thường 5-15 triệu VND/lượng.
        """
        sjc = self._get_latest_sjc()
        xau = self._get_latest_xau()

        if sjc and xau:
            usd_vnd = self._get_latest_usd_vnd() or 25_800
            world_price = xau["close"] * usd_vnd * LUONG_PER_OUNCE
            actual_premium = sjc["sell_price"] - world_price
            if 0 < actual_premium < 50_000_000:  # Sanity check < 50M
                return actual_premium

        # Default premium: ~10 triệu VND (trung bình lịch sử)
        return 10_000_000
