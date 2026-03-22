"""
Gold Predictor - Database Models (SQLAlchemy ORM)
Định nghĩa tất cả tables cho hệ thống dự đoán giá vàng.

Điểm mở rộng tương lai:
- Thêm table user_portfolios khi có tính năng quản lý portfolio
- Thêm table alerts cho price alert feature
- Migrate sang PostgreSQL + TimescaleDB (hypertables) cho production
"""

from datetime import datetime, date
from sqlalchemy import (
    Column, Integer, Float, String, DateTime, Date,
    Text, Boolean, Index, UniqueConstraint
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class cho tất cả models."""
    pass


class GoldPrice(Base):
    """
    Giá vàng XAU/USD và SJC.
    Lưu dữ liệu OHLCV cho XAU/USD, giá mua/bán cho SJC.
    """
    __tablename__ = "gold_prices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False, index=True)
    source = Column(String(20), nullable=False)  # "xau_usd" or "sjc"

    # OHLCV (chủ yếu cho XAU/USD)
    open = Column(Float, nullable=True)
    high = Column(Float, nullable=True)
    low = Column(Float, nullable=True)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=True)

    # SJC specific (giá mua/bán, đơn vị: triệu VND/lượng)
    buy_price = Column(Float, nullable=True)
    sell_price = Column(Float, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("date", "source", name="uq_gold_date_source"),
        Index("ix_gold_date_source", "date", "source"),
    )

    def __repr__(self):
        return f"<GoldPrice(date={self.date}, source={self.source}, close={self.close})>"


class MacroIndicator(Base):
    """
    Chỉ số macro kinh tế ảnh hưởng giá vàng.
    DXY, USD/VND, Oil, US 10Y Treasury, S&P 500.
    """
    __tablename__ = "macro_indicators"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False, index=True)
    indicator = Column(String(30), nullable=False)  # "dxy", "usd_vnd", "oil_wti", "us_10y", "sp500"

    # OHLCV
    open = Column(Float, nullable=True)
    high = Column(Float, nullable=True)
    low = Column(Float, nullable=True)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("date", "indicator", name="uq_macro_date_indicator"),
        Index("ix_macro_date_indicator", "date", "indicator"),
    )

    def __repr__(self):
        return f"<MacroIndicator(date={self.date}, indicator={self.indicator}, close={self.close})>"


class Prediction(Base):
    """
    Lưu trữ kết quả dự đoán từ ML models.
    Mỗi record = 1 dự đoán cho 1 target tại 1 thời điểm.
    """
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Target info
    target = Column(String(20), nullable=False)   # "xau_usd", "sjc"
    horizon = Column(String(10), nullable=False)   # "1d", "7d", "30d"

    # Price prediction (regression)
    predicted_price = Column(Float, nullable=True)
    confidence_lower = Column(Float, nullable=True)  # Lower bound CI
    confidence_upper = Column(Float, nullable=True)  # Upper bound CI

    # Trend prediction (classification)
    trend_up_prob = Column(Float, nullable=True)     # P(tăng)
    trend_down_prob = Column(Float, nullable=True)    # P(giảm)
    trend_sideway_prob = Column(Float, nullable=True)  # P(sideway)
    predicted_trend = Column(String(10), nullable=True)  # "Tăng", "Giảm", "Sideway"

    # Volatility prediction
    predicted_volatility = Column(Float, nullable=True)
    volatility_class = Column(String(15), nullable=True)  # "Thấp", "Trung bình", "Cao"

    # Model info
    model_name = Column(String(50), nullable=True)   # "ensemble", "xgboost", "lstm"
    model_version = Column(String(20), nullable=True)

    # Actual values (filled in later for evaluation)
    actual_price = Column(Float, nullable=True)
    actual_trend = Column(String(10), nullable=True)

    __table_args__ = (
        Index("ix_pred_target_horizon", "target", "horizon"),
        Index("ix_pred_created", "created_at"),
    )

    def __repr__(self):
        return f"<Prediction(target={self.target}, horizon={self.horizon}, price={self.predicted_price})>"


class NewsArticle(Base):
    """
    Tin tức tài chính liên quan đến vàng.
    Dùng cho AI sentiment analysis.
    """
    __tablename__ = "news_articles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    published_at = Column(DateTime, nullable=False, index=True)
    source = Column(String(50), nullable=False)      # "cafef", "kitco", "google_news"
    title = Column(String(500), nullable=False)
    url = Column(String(1000), nullable=True)
    summary = Column(Text, nullable=True)

    # AI Sentiment analysis results
    sentiment_score = Column(Float, nullable=True)     # -1.0 (bearish) to +1.0 (bullish)
    sentiment_label = Column(String(20), nullable=True)  # "bullish", "bearish", "neutral"
    analyzed_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_news_published", "published_at"),
        Index("ix_news_source", "source"),
    )

    def __repr__(self):
        return f"<NewsArticle(source={self.source}, title={self.title[:50]})>"


class AIAnalysis(Base):
    """
    Lưu trữ kết quả phân tích từ AI (Gemini/DeepSeek).
    """
    __tablename__ = "ai_analyses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    analysis_type = Column(String(30), nullable=False)  # "market", "sentiment", "advice"
    ai_provider = Column(String(20), nullable=False)     # "gemini", "deepseek"

    # Input context summary
    input_summary = Column(Text, nullable=True)

    # AI output
    analysis_text = Column(Text, nullable=False)          # Full analysis text
    recommendation = Column(String(20), nullable=True)    # BUY/SELL/HOLD
    confidence_score = Column(Float, nullable=True)       # 0.0 - 1.0
    risk_level = Column(String(20), nullable=True)        # LOW/MEDIUM/HIGH

    # Structured insights (JSON string)
    insights_json = Column(Text, nullable=True)

    __table_args__ = (
        Index("ix_ai_created", "created_at"),
        Index("ix_ai_type", "analysis_type"),
    )

    def __repr__(self):
        return f"<AIAnalysis(type={self.analysis_type}, rec={self.recommendation})>"
