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
    "dxy": "Chỉ số USD (DXY)",
    "dxy_change_1d": "DXY thay đổi 1 ngày",
    "dxy_change_5d": "DXY thay đổi 5 ngày",
    "dxy_rsi_14": "DXY RSI",
    "oil_wti": "Giá dầu WTI",
    "oil_wti_change_1d": "Giá dầu thay đổi 1 ngày",
    "oil_wti_change_5d": "Giá dầu thay đổi 5 ngày",
    "us_10y": "Lãi suất US 10Y",
    "us_10y_change_1d": "Lãi suất 10Y thay đổi 1 ngày",
    "usd_vnd": "Tỷ giá USD/VND",
    "usd_vnd_change_1d": "Tỷ giá USD/VND thay đổi",
    "sp500": "Chỉ số S&P 500",
    "sp500_change_1d": "S&P 500 thay đổi 1 ngày",
    "gold_dxy_ratio": "Tỉ lệ Vàng/DXY",
    "gold_dxy_ratio_change": "Vàng/DXY thay đổi",
    "gold_oil_ratio": "Tỉ lệ Vàng/Dầu",
    # Technical
    "rsi": "RSI (14)",
    "macd": "MACD",
    "macd_histogram": "MACD Histogram",
    "bb_position": "Vị trí Bollinger Band",
    "bb_width": "Độ rộng Bollinger Band",
    "atr_pct": "Biến động ATR %",
    "sma_50_above_200": "Golden Cross (SMA 50>200)",
    "price_to_sma_200": "Giá so với SMA 200 (%)",
    "stoch_k": "Stochastic %K",
    "williams_r": "Williams %R",
    # Price/Volume
    "close": "Giá đóng cửa",
    "volume": "Khối lượng giao dịch",
    "return_1d": "Lợi nhuận 1 ngày (%)",
    "return_5d": "Lợi nhuận 5 ngày (%)",
    "return_20d": "Lợi nhuận 20 ngày (%)",
    "volatility_5d": "Biến động 5 ngày",
    "volatility_20d": "Biến động 20 ngày",
    # Calendar
    "day_of_week": "Ngày trong tuần",
    "month": "Tháng",
    "quarter": "Quý",
}

# Mapping feature → macro context (tại sao ảnh hưởng vàng)
FEATURE_CONTEXT = {
    "dxy": "USD mạnh thường làm vàng giảm (nghịch biến)",
    "oil_wti": "Dầu tăng → lạm phát kỳ vọng tăng → vàng tăng",
    "us_10y": "Lãi suất tăng → chi phí cơ hội giữ vàng tăng → vàng giảm",
    "sp500": "Chứng khoán tăng → risk appetite cao → vàng giảm (safe-haven giảm)",
    "usd_vnd": "USD/VND tăng → giá vàng VN tăng theo",
    "rsi": "RSI > 70: quá mua (có thể giảm), RSI < 30: quá bán (có thể tăng)",
    "sma_50_above_200": "Golden Cross → xu hướng tăng dài hạn",
    "gold_dxy_ratio": "Tỉ lệ cao → vàng đắt so với USD",
    "atr_pct": "Biến động cao → rủi ro lớn",
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
                "summary": f"Không thể giải thích dự đoán: {str(e)}",
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
                "impact": "cao" if abs(shap_val) > np.mean(np.abs(shap_values)) * 2 else "trung bình",
                "context": context,
            }
            drivers.append(driver)

        return drivers

    def _build_summary(self, drivers: list, model_type: str) -> str:
        """Tạo summary text từ drivers."""
        if not drivers:
            return "Không đủ dữ liệu để giải thích."

        # Top bullish và bearish drivers
        bullish = [d for d in drivers if d["direction"] == "tang"]
        bearish = [d for d in drivers if d["direction"] == "giam"]

        parts = []
        parts.append("YẾU TỐ CHÍNH ẢNH HƯỞNG DỰ ĐOÁN:")

        if bullish:
            parts.append("\n📈 Đẩy giá TĂNG:")
            for d in bullish[:3]:
                ctx = f" ({d['context']})" if d['context'] else ""
                parts.append(f"  + {d['display_name']} = {d['value']}{ctx}")

        if bearish:
            parts.append("\n📉 Đẩy giá GIẢM:")
            for d in bearish[:3]:
                ctx = f" ({d['context']})" if d['context'] else ""
                parts.append(f"  - {d['display_name']} = {d['value']}{ctx}")

        return "\n".join(parts)
