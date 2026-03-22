"""
Gold Predictor - API Schemas (Pydantic)
Request/response models cho FastAPI endpoints.
"""

from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field


# ===== Gold Price =====

class GoldPriceResponse(BaseModel):
    date: date
    source: str
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: float
    volume: Optional[float] = None
    buy_price: Optional[float] = None
    sell_price: Optional[float] = None


class GoldPriceListResponse(BaseModel):
    data: list[GoldPriceResponse]
    count: int
    source: str


# ===== Prediction =====

class TrendProbabilities(BaseModel):
    giam: float = Field(description="P(Giam)")
    sideway: float = Field(description="P(Sideway)")
    tang: float = Field(description="P(Tang)")


class PredictionResponse(BaseModel):
    date: str
    horizon: str
    predicted_price: float
    confidence_lower: float
    confidence_upper: float
    predicted_trend: int = Field(description="0=Giam, 1=Sideway, 2=Tang")
    trend_label: str = Field(description="Giam/Sideway/Tang")
    trend_probabilities: TrendProbabilities


class PredictionAllHorizonsResponse(BaseModel):
    predictions: dict[str, PredictionResponse]
    current_price: float
    generated_at: str


# ===== Market Analysis =====

class TechnicalSnapshot(BaseModel):
    rsi: float
    macd: float
    macd_signal: float
    bb_position: float
    atr_pct: float
    sma_50_above_200: int
    price_to_sma_200: float


class AnalysisResponse(BaseModel):
    analysis_type: str
    ai_provider: str
    analysis_text: str
    recommendation: str
    confidence_score: float
    risk_level: str
    score: int
    timestamp: str


# ===== Investment Advice =====

class AdviceResponse(BaseModel):
    timestamp: str
    source: str
    horizon: str
    current_price: float
    recommendation: str
    confidence: float
    risk_level: str
    summary: str
    analysis: AnalysisResponse
    prediction: Optional[PredictionResponse] = None
    technical_snapshot: TechnicalSnapshot


# ===== System =====

class TrainRequest(BaseModel):
    horizon: str = Field(default="7d", description="1d, 7d, or 30d")
    source: str = Field(default="xau_usd")


class TrainResponse(BaseModel):
    status: str
    horizon: str
    metrics: dict
    message: str


class CollectDataResponse(BaseModel):
    status: str
    results: dict
    message: str
