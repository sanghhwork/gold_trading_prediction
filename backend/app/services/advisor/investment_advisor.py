"""
Gold Predictor - Investment Advisor
Tạo lời khuyên đầu tư dựa trên ML predictions + market analysis.

Điểm mở rộng tương lai:
- Thêm portfolio-level advice
- Thêm risk-adjusted sizing
- Thêm historical win-rate tracking
"""

from datetime import datetime
from typing import Optional

from app.services.ai_reasoning.market_analyzer import MarketAnalyzer
from app.services.models.model_trainer import ModelTrainer
from app.services.feature_engine.feature_builder import FeatureBuilder
from app.db.database import get_session_factory
from app.db.models import GoldPrice
from app.utils.constants import PREDICTION_HORIZONS, TREND_LABELS
from app.utils.logger import get_logger

logger = get_logger(__name__)


class InvestmentAdvisor:
    """
    Tạo lời khuyên đầu tư tổng hợp.
    Kết hợp ML prediction + technical analysis + market context.
    """

    def __init__(self):
        self.logger = get_logger("investment_advisor")
        self.analyzer = MarketAnalyzer()
        self.feature_builder = FeatureBuilder()

    def get_advice(
        self,
        trainer: Optional[ModelTrainer] = None,
        horizon: str = "7d",
        source: str = "xau_usd",
    ) -> dict:
        """
        Tạo lời khuyên đầu tư đầy đủ.

        Returns:
            dict với summary, recommendation, analysis, predictions
        """
        self.logger.info(f"Generating investment advice ({horizon})...")

        # 1. Build features
        df = self.feature_builder.build_features(source=source, include_macro=True)
        if df.empty:
            return self._empty_advice("Khong co du lieu")

        # 2. Get latest features
        latest_row = df.iloc[-1]
        latest_features = latest_row.to_dict()

        # 3. Get current price
        current_price = latest_features.get("close", 0)

        # 4. Get ML prediction (nếu có trainer)
        prediction = {}
        if trainer and horizon in trainer.trained_models:
            try:
                prediction = trainer.predict(horizon=horizon, source=source)
            except Exception as e:
                self.logger.warning(f"Prediction error: {e}")

        # 5. Market analysis
        analysis = self.analyzer.analyze(latest_features, prediction)

        # 6. Build advice
        advice = self._build_advice(
            current_price=current_price,
            prediction=prediction,
            analysis=analysis,
            features=latest_features,
            horizon=horizon,
            source=source,
        )

        self.logger.info(
            f"Advice generated: {advice['recommendation']} "
            f"(confidence={advice['confidence']:.0%})"
        )
        return advice

    def _build_advice(
        self,
        current_price: float,
        prediction: dict,
        analysis: dict,
        features: dict,
        horizon: str,
        source: str,
    ) -> dict:
        """Tổng hợp thành lời khuyên."""
        rec = analysis.get("recommendation", "HOLD")
        confidence = analysis.get("confidence_score", 0)
        risk = analysis.get("risk_level", "MEDIUM")

        # Format summary
        summary_parts = []

        # Current state
        summary_parts.append(f"Gia hien tai: ${current_price:,.2f}")

        # Trend
        rsi = features.get("rsi", 50)
        macd_above = features.get("macd_above_signal", 0)
        sma_cross = features.get("sma_50_above_200", 0)

        if sma_cross:
            summary_parts.append("Xu huong dai han: TANG (Golden Cross)")
        else:
            summary_parts.append("Xu huong dai han: GIAM (Death Cross)")

        # Prediction
        if prediction.get("predicted_price"):
            pred_price = prediction["predicted_price"]
            change_pct = (pred_price - current_price) / current_price * 100
            direction = "tang" if change_pct > 0 else "giam"
            summary_parts.append(
                f"Du doan {horizon}: ${pred_price:,.2f} ({direction} {abs(change_pct):.1f}%)"
            )

        # Recommendation text
        rec_text = {
            "STRONG_BUY": "KHUYEN NGHI MUA MANH - Nhieu tin hieu tang cung luc",
            "BUY": "KHUYEN NGHI MUA - Xu huong tich cuc, co the tich luy",
            "HOLD": "KHUYEN NGHI GIU - Thi truong chua ro xu huong",
            "SELL": "KHUYEN NGHI BAN - Tin hieu giam, can than",
            "STRONG_SELL": "KHUYEN NGHI BAN MANH - Nhieu tin hieu giam cung luc",
        }.get(rec, "GIU")

        summary_parts.append(f"\n>> {rec_text}")

        # Risk warning
        if risk in ("HIGH", "VERY_HIGH"):
            summary_parts.append(
                "\n⚠ LUU Y: Bien dong cao, chi dau tu so tien san sang mat. "
                "Dat stop-loss."
            )

        return {
            "timestamp": datetime.now().isoformat(),
            "source": source,
            "horizon": horizon,
            "current_price": round(current_price, 2),
            "recommendation": rec,
            "confidence": round(confidence, 2),
            "risk_level": risk,
            "summary": "\n".join(summary_parts),
            "analysis": analysis,
            "prediction": prediction,
            "technical_snapshot": {
                "rsi": round(features.get("rsi", 0), 2),
                "macd": round(features.get("macd", 0), 2),
                "macd_signal": round(features.get("macd_signal", 0), 2),
                "bb_position": round(features.get("bb_position", 0), 4),
                "atr_pct": round(features.get("atr_pct", 0), 4),
                "sma_50_above_200": int(features.get("sma_50_above_200", 0)),
                "price_to_sma_200": round(features.get("price_to_sma_200", 0), 2),
            },
        }

    def _empty_advice(self, reason: str) -> dict:
        """Return empty advice khi không có data."""
        return {
            "timestamp": datetime.now().isoformat(),
            "recommendation": "HOLD",
            "confidence": 0,
            "risk_level": "HIGH",
            "summary": f"Khong the tao loi khuyen: {reason}",
            "analysis": {},
            "prediction": {},
            "technical_snapshot": {},
        }
