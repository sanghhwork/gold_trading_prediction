"""
Gold Predictor - Prediction Explainer
Giải thích TẠI SAO model dự đoán tăng/giảm bằng SHAP values.

Output: Danh sách các yếu tố chính ảnh hưởng đến dự đoán,
kèm hướng tác động (tăng/giảm) và mức độ.

VD: "Giá dầu tăng 5% → đẩy vàng tăng (contribution: +$120)"

Điểm mở rộng tương lai:
- Thêm SHAP waterfall plot (visualization)
- Thêm interaction effects
- Thêm temporal SHAP (how explanations change over time)
"""

from typing import Optional

import numpy as np
import pandas as pd
import shap

from app.utils.logger import get_logger

logger = get_logger(__name__)

# Mapping feature names → human-readable descriptions (tiếng Việt)
FEATURE_DESCRIPTIONS = {
    # Macro
    "dxy": "Chi so USD (DXY)",
    "dxy_change_1d": "DXY thay doi 1 ngay",
    "dxy_change_5d": "DXY thay doi 5 ngay",
    "dxy_rsi_14": "DXY RSI",
    "oil_wti": "Gia dau WTI",
    "oil_wti_change_1d": "Gia dau thay doi 1 ngay",
    "oil_wti_change_5d": "Gia dau thay doi 5 ngay",
    "us_10y": "Lai suat US 10Y",
    "us_10y_change_1d": "Lai suat 10Y thay doi 1 ngay",
    "usd_vnd": "Ty gia USD/VND",
    "usd_vnd_change_1d": "Ty gia USD/VND thay doi",
    "sp500": "Chi so S&P 500",
    "sp500_change_1d": "S&P 500 thay doi 1 ngay",
    "gold_dxy_ratio": "Ti le Vang/DXY",
    "gold_dxy_ratio_change": "Vang/DXY thay doi",
    "gold_oil_ratio": "Ti le Vang/Dau",
    # Technical
    "rsi": "RSI (14)",
    "macd": "MACD",
    "macd_histogram": "MACD Histogram",
    "bb_position": "Vi tri Bollinger Band",
    "bb_width": "Do rong Bollinger Band",
    "atr_pct": "Bien dong ATR %",
    "sma_50_above_200": "Golden Cross (SMA 50>200)",
    "price_to_sma_200": "Gia so voi SMA 200 (%)",
    "stoch_k": "Stochastic %K",
    "williams_r": "Williams %R",
    # Price/Volume
    "close": "Gia dong cua",
    "volume": "Khoi luong giao dich",
    "return_1d": "Loi nhuan 1 ngay (%)",
    "return_5d": "Loi nhuan 5 ngay (%)",
    "return_20d": "Loi nhuan 20 ngay (%)",
    "volatility_5d": "Bien dong 5 ngay",
    "volatility_20d": "Bien dong 20 ngay",
    # Calendar
    "day_of_week": "Ngay trong tuan",
    "month": "Thang",
    "quarter": "Quy",
}

# Mapping feature → macro context (tại sao ảnh hưởng vàng)
FEATURE_CONTEXT = {
    "dxy": "USD manh thuong lam vang giam (nghich bien)",
    "oil_wti": "Dau tang → lam phat ky vong tang → vang tang",
    "us_10y": "Lai suat tang → chi phi co hoi giu vang tang → vang giam",
    "sp500": "Chung khoan tang → risk appetite cao → vang giam (safe-haven giam)",
    "usd_vnd": "USD/VND tang → gia vang VN tang theo",
    "rsi": "RSI > 70: qua mua (co the giam), RSI < 30: qua ban (co the tang)",
    "sma_50_above_200": "Golden Cross → xu huong tang dai han",
    "gold_dxy_ratio": "Ti le cao → vang dat so voi USD",
    "atr_pct": "Bien dong cao → rui ro lon",
}


class PredictionExplainer:
    """
    Giải thích dự đoán bằng SHAP values.
    Cho biết TẠI SAO model dự đoán tăng/giảm.
    """

    def __init__(self):
        self.logger = get_logger("prediction_explainer")
        self._explainer_cache = {}

    def explain_prediction(
        self,
        model,
        X_latest: pd.DataFrame,
        top_n: int = 8,
    ) -> dict:
        """
        Giải thích 1 prediction cụ thể.

        Args:
            model: Trained model (phải có .model attribute là XGBoost)
            X_latest: Features của dữ liệu cần giải thích (1 row)
            top_n: Số features quan trọng nhất hiển thị

        Returns:
            dict với drivers (danh sách yếu tố), summary text
        """
        self.logger.info(f"Generating SHAP explanation for {model.name}...")

        try:
            # Tạo SHAP explainer
            xgb_model = model.model
            explainer = shap.TreeExplainer(xgb_model)

            # Tính SHAP values
            shap_values = explainer.shap_values(X_latest)

            # Nếu classification (multi-output), lấy class có xác suất cao nhất
            if isinstance(shap_values, list):
                # Multi-class: lấy SHAP values cho class được predict
                pred = model.predict(X_latest)[0]
                shap_vals = shap_values[int(pred)][0]
            else:
                shap_vals = shap_values[0]

            # Build driver list
            feature_names = list(X_latest.columns)
            drivers = self._build_drivers(
                feature_names, shap_vals, X_latest.iloc[0], top_n
            )

            # Summary text
            summary = self._build_summary(drivers, model.model_type)

            result = {
                "model_name": model.name,
                "drivers": drivers,
                "summary": summary,
                "base_value": float(explainer.expected_value) if not isinstance(explainer.expected_value, list) else float(explainer.expected_value[0]),
            }

            self.logger.info(f"SHAP explanation: {len(drivers)} key drivers found")
            return result

        except Exception as e:
            self.logger.error(f"SHAP explanation error: {e}")
            return {
                "model_name": model.name,
                "drivers": [],
                "summary": f"Khong the giai thich du doan: {str(e)}",
                "base_value": 0,
            }

    def _build_drivers(
        self,
        feature_names: list,
        shap_values: np.ndarray,
        feature_values: pd.Series,
        top_n: int,
    ) -> list[dict]:
        """Tạo danh sách drivers (yếu tố ảnh hưởng) sorted by importance."""
        # Pair features with SHAP values
        pairs = list(zip(feature_names, shap_values, feature_values))

        # Sort by absolute SHAP value
        pairs.sort(key=lambda x: abs(x[1]), reverse=True)

        drivers = []
        for name, shap_val, feat_val in pairs[:top_n]:
            direction = "tang" if shap_val > 0 else "giam"
            human_name = FEATURE_DESCRIPTIONS.get(name, name)
            context = FEATURE_CONTEXT.get(name, "")

            driver = {
                "feature": name,
                "display_name": human_name,
                "value": round(float(feat_val), 4),
                "shap_value": round(float(shap_val), 4),
                "direction": direction,
                "impact": "cao" if abs(shap_val) > np.mean(np.abs(shap_values)) * 2 else "trung binh",
                "context": context,
            }
            drivers.append(driver)

        return drivers

    def _build_summary(self, drivers: list, model_type: str) -> str:
        """Tạo summary text từ drivers."""
        if not drivers:
            return "Khong du du lieu de giai thich."

        # Top bullish và bearish drivers
        bullish = [d for d in drivers if d["direction"] == "tang"]
        bearish = [d for d in drivers if d["direction"] == "giam"]

        parts = []
        parts.append("YEU TO CHINH ANH HUONG DU DOAN:")

        if bullish:
            parts.append("\n📈 Day gia TANG:")
            for d in bullish[:3]:
                ctx = f" ({d['context']})" if d['context'] else ""
                parts.append(f"  + {d['display_name']} = {d['value']}{ctx}")

        if bearish:
            parts.append("\n📉 Day gia GIAM:")
            for d in bearish[:3]:
                ctx = f" ({d['context']})" if d['context'] else ""
                parts.append(f"  - {d['display_name']} = {d['value']}{ctx}")

        return "\n".join(parts)
