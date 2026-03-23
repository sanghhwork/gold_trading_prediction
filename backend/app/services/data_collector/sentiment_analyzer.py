"""
Gold Predictor - Sentiment Analyzer
Phân tích sentiment tin tức vàng bằng Gemini AI.

DB Schema (đã có sẵn trong NewsArticle):
- sentiment_score: Float (-1.0 → +1.0)
- sentiment_label: String ("bullish"/"bearish"/"neutral")
- analyzed_at: DateTime

Điểm mở rộng tương lai:
- Swap sang FinBERT / PhoBERT cho Vietnamese
- Thêm batch processing
- Thêm sentiment history tracking
"""

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.db.database import get_session_factory
from app.db.models import NewsArticle
from app.utils.logger import get_logger

logger = get_logger(__name__)


class SentimentAnalyzer:
    """
    Phân tích sentiment cho tin tức vàng.
    
    Sử dụng Gemini AI (đã có client) để phân tích.
    Fallback: rule-based keyword matching.
    """

    # Keywords cho rule-based fallback
    BULLISH_KEYWORDS = [
        "tăng", "tăng giá", "tăng mạnh", "tăng vọt", "cao", "cao nhất",
        "kỷ lục", "surge", "rally", "bullish", "soar", "gain", "rise",
        "mua vào", "tích cực", "lạc quan", "hỗ trợ", "support",
        "demand", "nhu cầu tăng", "gold rises", "all-time high",
    ]

    BEARISH_KEYWORDS = [
        "giảm", "giảm giá", "giảm mạnh", "giảm sâu", "thấp", "thấp nhất",
        "lao dốc", "crash", "bearish", "drop", "fall", "decline", "plunge",
        "bán ra", "tiêu cực", "bi quan", "áp lực", "resistance",
        "supply", "sell-off", "gold falls", "gold drops",
    ]

    def __init__(self):
        self.logger = get_logger("sentiment_analyzer")
        self._gemini_client = None

    def _get_gemini_client(self):
        """Lazy init Gemini client."""
        if self._gemini_client is None:
            try:
                from app.services.ai_reasoning.gemini_client import GeminiClient
                self._gemini_client = GeminiClient()
                self.logger.info("Gemini client initialized cho sentiment analysis")
            except Exception as e:
                self.logger.warning(f"Không thể init Gemini client: {e}. Dùng rule-based fallback.")
        return self._gemini_client

    def analyze_text(self, title: str, summary: Optional[str] = None) -> dict:
        """
        Phân tích sentiment cho 1 tin tức.
        
        Returns:
            { "score": float, "label": str }
            score: -1.0 (bearish) to +1.0 (bullish)
            label: "bullish" / "bearish" / "neutral"
        """
        # Try Gemini AI first
        gemini = self._get_gemini_client()
        if gemini:
            try:
                return self._analyze_with_gemini(title, summary)
            except Exception as e:
                self.logger.warning(f"Gemini sentiment failed: {e}. Dùng rule-based.")
        
        # Fallback: rule-based
        return self._analyze_rule_based(title, summary)

    def _analyze_with_gemini(self, title: str, summary: Optional[str] = None) -> dict:
        """Phân tích sentiment bằng Gemini AI."""
        text = title
        if summary:
            text += f"\n{summary}"

        prompt = f"""Analyze the sentiment of this gold/financial news for gold price impact.
Respond with ONLY a JSON object (no markdown, no explanation):
{{"score": <float between -1.0 and 1.0>, "label": "<bullish|bearish|neutral>"}}

Where:
- score > 0.3 = bullish (positive for gold price)
- score < -0.3 = bearish (negative for gold price)
- else = neutral

News: {text}"""

        gemini = self._get_gemini_client()
        response = gemini.generate(prompt)
        
        # Parse JSON response
        import json
        import re
        
        # Extract JSON from response
        json_match = re.search(r'\{[^}]+\}', response)
        if json_match:
            result = json.loads(json_match.group())
            score = max(-1.0, min(1.0, float(result.get("score", 0))))
            label = result.get("label", "neutral")
            if label not in ("bullish", "bearish", "neutral"):
                label = "neutral"
            return {"score": score, "label": label}
        
        # Fallback if can't parse
        return self._analyze_rule_based(title, summary)

    def _analyze_rule_based(self, title: str, summary: Optional[str] = None) -> dict:
        """Rule-based sentiment (fallback when AI not available)."""
        text = (title + " " + (summary or "")).lower()
        
        bullish_count = sum(1 for kw in self.BULLISH_KEYWORDS if kw in text)
        bearish_count = sum(1 for kw in self.BEARISH_KEYWORDS if kw in text)
        
        total = bullish_count + bearish_count
        if total == 0:
            return {"score": 0.0, "label": "neutral"}
        
        # Score = (bullish - bearish) / total, scaled to [-1, 1]
        score = (bullish_count - bearish_count) / total
        
        if score > 0.2:
            label = "bullish"
        elif score < -0.2:
            label = "bearish"
        else:
            label = "neutral"
        
        return {"score": round(score, 4), "label": label}

    def analyze_unanalyzed_articles(self, limit: int = 50) -> int:
        """
        Phân tích sentiment cho các articles chưa analyzed trong DB.
        
        Returns: số articles đã phân tích
        """
        SessionLocal = get_session_factory()
        db = SessionLocal()
        
        try:
            # Lấy articles chưa có sentiment
            articles = db.query(NewsArticle).filter(
                NewsArticle.sentiment_score.is_(None)
            ).order_by(
                NewsArticle.published_at.desc()
            ).limit(limit).all()

            if not articles:
                self.logger.info("Không có articles chưa phân tích sentiment")
                return 0

            count = 0
            for article in articles:
                try:
                    result = self.analyze_text(article.title, article.summary)
                    article.sentiment_score = result["score"]
                    article.sentiment_label = result["label"]
                    article.analyzed_at = datetime.utcnow()
                    count += 1
                    
                    self.logger.debug(
                        f"Analyzed: [{result['label']}] ({result['score']:+.2f}) {article.title[:60]}..."
                    )
                except Exception as e:
                    self.logger.warning(f"Lỗi analyze article {article.id}: {e}")
                    continue

            db.commit()
            self.logger.info(f"Đã phân tích sentiment cho {count}/{len(articles)} articles")
            return count

        except Exception as e:
            db.rollback()
            self.logger.error(f"Lỗi analyze_unanalyzed_articles: {e}")
            return 0
        finally:
            db.close()

    def get_daily_sentiment(self, days: int = 7) -> dict:
        """
        Lấy sentiment trung bình theo ngày (cho feature engineering).
        
        Returns:
            { "2026-03-23": {"avg_score": 0.35, "count": 5, "bullish_pct": 0.6}, ... }
        """
        from datetime import timedelta
        from sqlalchemy import func, cast, Date
        
        SessionLocal = get_session_factory()
        db = SessionLocal()
        
        try:
            cutoff = datetime.utcnow() - timedelta(days=days)
            
            results = db.query(
                cast(NewsArticle.published_at, Date).label("date"),
                func.avg(NewsArticle.sentiment_score).label("avg_score"),
                func.count(NewsArticle.id).label("count"),
            ).filter(
                NewsArticle.analyzed_at.isnot(None),
                NewsArticle.published_at >= cutoff,
            ).group_by(
                cast(NewsArticle.published_at, Date)
            ).order_by(
                cast(NewsArticle.published_at, Date).desc()
            ).all()

            daily = {}
            for row in results:
                daily[str(row.date)] = {
                    "avg_score": round(float(row.avg_score or 0), 4),
                    "count": row.count,
                }
            
            return daily
        finally:
            db.close()
