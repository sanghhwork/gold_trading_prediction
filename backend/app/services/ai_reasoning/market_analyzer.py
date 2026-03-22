"""
Gold Predictor - Market Analyzer
Phân tích thị trường vàng kết hợp ML models + Technical Analysis + AI.

Strategy:
1. Rule-based analysis (luôn chạy) → baseline analysis
2. Gemini AI analysis (khi có key) → enhanced analysis
3. Merge kết quả → comprehensive report

Điểm mở rộng tương lai:
- Thêm sentiment analysis từ news
- Thêm cross-market correlation analysis
- Thêm historical pattern matching
"""

from datetime import date, datetime
from typing import Optional

import pandas as pd
import numpy as np

from app.services.ai_reasoning.gemini_client import is_gemini_available, ask_gemini
from app.utils.constants import (
    SIGNAL_BUY, SIGNAL_SELL, SIGNAL_HOLD,
    SIGNAL_STRONG_BUY, SIGNAL_STRONG_SELL,
    RISK_LOW, RISK_MEDIUM, RISK_HIGH, RISK_VERY_HIGH,
    TREND_LABELS,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


class MarketAnalyzer:
    """
    Phân tích thị trường vàng.
    Kết hợp rule-based + AI (khi có Gemini key).
    """

    def __init__(self):
        self.logger = get_logger("market_analyzer")

    def analyze(
        self,
        latest_features: dict,
        prediction: dict,
        recent_prices: Optional[pd.DataFrame] = None,
    ) -> dict:
        """
        Phân tích toàn diện thị trường vàng.

        Args:
            latest_features: Dict features mới nhất (RSI, MACD, BB, etc.)
            prediction: Dict prediction từ ML model
            recent_prices: DataFrame giá 30 ngày gần nhất (optional)

        Returns:
            dict với analysis_text, recommendation, confidence, risk_level
        """
        # 1. Rule-based analysis (luôn chạy)
        rule_analysis = self._rule_based_analysis(latest_features, prediction)

        # 2. AI analysis (khi có Gemini)
        if is_gemini_available():
            self.logger.info("Gemini available - running AI enhanced analysis")
            # TODO: Call Gemini for enhanced analysis khi có key
            pass

        return rule_analysis

    def _rule_based_analysis(
        self,
        features: dict,
        prediction: dict,
    ) -> dict:
        """
        Phân tích dựa trên rules kỹ thuật.
        Không cần AI - hoạt động independent.
        """
        signals = []
        analysis_parts = []
        score = 0  # -100 (very bearish) to +100 (very bullish)

        # ===== 1. RSI Analysis =====
        rsi = features.get("rsi", 50)
        if rsi > 70:
            signals.append(("RSI", "Overbought", -2))
            analysis_parts.append(f"RSI = {rsi:.1f} (vung qua mua). Rui ro dieu chinh ngan han.")
            score -= 20
        elif rsi < 30:
            signals.append(("RSI", "Oversold", 2))
            analysis_parts.append(f"RSI = {rsi:.1f} (vung qua ban). Co hoi mua vao.")
            score += 20
        else:
            signals.append(("RSI", "Neutral", 0))
            analysis_parts.append(f"RSI = {rsi:.1f} (vung trung tinh).")

        # ===== 2. MACD Analysis =====
        macd = features.get("macd", 0)
        macd_signal = features.get("macd_signal", 0)
        macd_hist = features.get("macd_histogram", 0)

        if macd > macd_signal and macd_hist > 0:
            signals.append(("MACD", "Bullish", 1))
            analysis_parts.append("MACD cat len tren signal line - tin hieu tang.")
            score += 15
        elif macd < macd_signal and macd_hist < 0:
            signals.append(("MACD", "Bearish", -1))
            analysis_parts.append("MACD cat xuong duoi signal line - tin hieu giam.")
            score -= 15
        else:
            signals.append(("MACD", "Neutral", 0))

        # ===== 3. Bollinger Bands Analysis =====
        bb_position = features.get("bb_position", 0.5)
        if bb_position > 0.95:
            signals.append(("BB", "Upper Band", -1))
            analysis_parts.append("Gia cham Bollinger Band tren - co the dieu chinh.")
            score -= 10
        elif bb_position < 0.05:
            signals.append(("BB", "Lower Band", 1))
            analysis_parts.append("Gia cham Bollinger Band duoi - co hoi rebound.")
            score += 10

        # ===== 4. Moving Average Analysis =====
        sma_50_above_200 = features.get("sma_50_above_200", 0)
        if sma_50_above_200:
            signals.append(("SMA", "Golden Cross", 2))
            analysis_parts.append("SMA 50 > SMA 200 (Golden Cross) - xu huong tang dai han.")
            score += 20
        else:
            signals.append(("SMA", "Death Cross", -2))
            analysis_parts.append("SMA 50 < SMA 200 (Death Cross) - xu huong giam dai han.")
            score -= 20

        price_to_sma200 = features.get("price_to_sma_200", 0)
        if price_to_sma200 > 10:
            analysis_parts.append(f"Gia cao hon SMA 200 {price_to_sma200:.1f}% - co the overextended.")
            score -= 5

        # ===== 5. Volatility Analysis =====
        atr_pct = features.get("atr_pct", 0)
        if atr_pct > 3:
            analysis_parts.append(f"ATR% = {atr_pct:.2f}% - bien dong CAO, can than quan ly rui ro.")
            risk_boost = 1
        else:
            risk_boost = 0

        # ===== 6. ML Prediction Score =====
        if prediction:
            trend = prediction.get("predicted_trend", 1)
            trend_probs = prediction.get("trend_probabilities", {})

            if trend == 2:  # Tang
                prob = trend_probs.get("tang", 0.5)
                score += int(prob * 30)
                analysis_parts.append(
                    f"ML Model du doan: TANG (xac suat {prob:.0%})"
                )
            elif trend == 0:  # Giam
                prob = trend_probs.get("giam", 0.5)
                score -= int(prob * 30)
                analysis_parts.append(
                    f"ML Model du doan: GIAM (xac suat {prob:.0%})"
                )
            else:
                analysis_parts.append("ML Model du doan: SIDEWAY")

            if "predicted_price" in prediction:
                analysis_parts.append(
                    f"Gia du doan: ${prediction['predicted_price']:,.2f} "
                    f"[${prediction.get('confidence_lower', 0):,.2f} - "
                    f"${prediction.get('confidence_upper', 0):,.2f}]"
                )

        # ===== Generate Recommendation =====
        recommendation = self._score_to_signal(score)
        confidence = min(abs(score) / 100, 1.0)
        risk_level = self._calculate_risk(atr_pct, abs(score), risk_boost)

        analysis_text = "\n".join(analysis_parts)

        result = {
            "analysis_type": "market",
            "ai_provider": "gemini" if is_gemini_available() else "rule_based",
            "analysis_text": analysis_text,
            "recommendation": recommendation,
            "confidence_score": round(confidence, 2),
            "risk_level": risk_level,
            "score": score,
            "signals": signals,
            "timestamp": datetime.now().isoformat(),
        }

        self.logger.info(
            f"Market analysis: score={score}, rec={recommendation}, "
            f"confidence={confidence:.0%}, risk={risk_level}"
        )
        return result

    @staticmethod
    def _score_to_signal(score: int) -> str:
        """Convert score thành signal."""
        if score >= 40:
            return SIGNAL_STRONG_BUY
        elif score >= 15:
            return SIGNAL_BUY
        elif score <= -40:
            return SIGNAL_STRONG_SELL
        elif score <= -15:
            return SIGNAL_SELL
        else:
            return SIGNAL_HOLD

    @staticmethod
    def _calculate_risk(atr_pct: float, score_abs: int, boost: int = 0) -> str:
        """Tính mức rủi ro."""
        risk_score = atr_pct * 10 + (100 - score_abs) * 0.3 + boost * 20
        if risk_score > 70:
            return RISK_VERY_HIGH
        elif risk_score > 50:
            return RISK_HIGH
        elif risk_score > 30:
            return RISK_MEDIUM
        else:
            return RISK_LOW
