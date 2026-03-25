"""
Gold Predictor - API Routes
FastAPI endpoints cho Gold Prediction system.
"""

from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.database import get_db
from app.db.models import GoldPrice, MacroIndicator
from app.api.schemas.gold_schemas import (
    GoldPriceResponse, GoldPriceListResponse,
    PredictionResponse, PredictionAllHorizonsResponse,
    TrendProbabilities, AnalysisResponse, AdviceResponse,
    TechnicalSnapshot, TrainRequest, TrainResponse,
    CollectDataResponse,
)
from app.utils.constants import PREDICTION_HORIZONS, TREND_LABELS
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Gold Prediction"])

# ===== Global state: trained models =====
_trainer = None


def _get_trainer():
    """Lazy init model trainer."""
    global _trainer
    if _trainer is None:
        from app.services.models.model_trainer import ModelTrainer
        _trainer = ModelTrainer()
    return _trainer


# ==========================================
# GOLD PRICES
# ==========================================

@router.get("/gold/prices", response_model=GoldPriceListResponse)
def get_gold_prices(
    source: str = Query(default="xau_usd", description="xau_usd or sjc"),
    days: int = Query(default=30, ge=1, le=1825, description="So ngay"),
    db: Session = Depends(get_db),
):
    """Lấy giá vàng N ngày gần nhất."""
    logger.info(f"GET /gold/prices source={source} days={days}")

    cutoff = date.today() - timedelta(days=days)
    records = db.query(GoldPrice).filter(
        GoldPrice.source == source,
        GoldPrice.date >= cutoff,
    ).order_by(GoldPrice.date).all()

    data = [GoldPriceResponse(
        date=r.date,
        source=r.source,
        open=r.open,
        high=r.high,
        low=r.low,
        close=r.close,
        volume=r.volume,
        buy_price=r.buy_price,
        sell_price=r.sell_price,
    ) for r in records]

    return GoldPriceListResponse(data=data, count=len(data), source=source)


@router.get("/gold/latest")
def get_latest_price(
    source: str = Query(default="xau_usd"),
    db: Session = Depends(get_db),
):
    """Lấy giá vàng mới nhất."""
    record = db.query(GoldPrice).filter_by(
        source=source
    ).order_by(GoldPrice.date.desc()).first()

    if not record:
        raise HTTPException(404, f"Không có dữ liệu cho {source}")

    return {
        "date": str(record.date),
        "source": record.source,
        "close": record.close,
        "open": record.open,
        "high": record.high,
        "low": record.low,
        "volume": record.volume,
        "buy_price": record.buy_price,
        "sell_price": record.sell_price,
    }


@router.get("/gold/summary")
def get_gold_summary(db: Session = Depends(get_db)):
    """Tổng quan dữ liệu vàng trong DB."""
    xau_count = db.query(func.count(GoldPrice.id)).filter_by(source="xau_usd").scalar()
    sjc_count = db.query(func.count(GoldPrice.id)).filter_by(source="sjc").scalar()
    macro_count = db.query(func.count(MacroIndicator.id)).scalar()

    xau_latest = db.query(GoldPrice).filter_by(source="xau_usd").order_by(GoldPrice.date.desc()).first()

    return {
        "xau_usd_records": xau_count,
        "sjc_records": sjc_count,
        "macro_records": macro_count,
        "latest_xau_price": xau_latest.close if xau_latest else None,
        "latest_xau_date": str(xau_latest.date) if xau_latest else None,
    }


# ==========================================
# PREDICTIONS
# ==========================================

@router.get("/predictions/{horizon}")
def get_prediction(horizon: str = "7d"):
    """Lấy prediction cho 1 horizon."""
    if horizon not in PREDICTION_HORIZONS:
        raise HTTPException(400, f"Invalid horizon. Valid: {list(PREDICTION_HORIZONS.keys())}")

    trainer = _get_trainer()

    # Auto-train nếu chưa train
    if horizon not in trainer.trained_models:
        logger.info(f"Auto-training models for {horizon}...")
        trainer.train_all(horizon=horizon)

    try:
        pred = trainer.predict(horizon=horizon)
        trend_map = {0: "Giảm", 1: "Đi ngang", 2: "Tăng"}

        return {
            "date": pred.get("date"),
            "horizon": horizon,
            "predicted_price": pred.get("predicted_price"),
            "confidence_lower": pred.get("confidence_lower"),
            "confidence_upper": pred.get("confidence_upper"),
            "predicted_trend": pred.get("predicted_trend"),
            "trend_label": trend_map.get(pred.get("predicted_trend", 1), "Đi ngang"),
            "trend_probabilities": pred.get("trend_probabilities"),
        }
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(500, str(e))


@router.get("/predictions")
def get_all_predictions():
    """Lấy predictions cho tất cả horizons."""
    trainer = _get_trainer()
    results = {}

    for horizon in PREDICTION_HORIZONS:
        try:
            if horizon not in trainer.trained_models:
                trainer.train_all(horizon=horizon)
            pred = trainer.predict(horizon=horizon)
            trend_map = {0: "Giảm", 1: "Đi ngang", 2: "Tăng"}
            results[horizon] = {
                "predicted_price": pred.get("predicted_price"),
                "confidence_lower": pred.get("confidence_lower"),
                "confidence_upper": pred.get("confidence_upper"),
                "predicted_trend": pred.get("predicted_trend"),
                "trend_label": trend_map.get(pred.get("predicted_trend", 1)),
                "trend_probabilities": pred.get("trend_probabilities"),
            }
        except Exception as e:
            logger.error(f"Prediction error ({horizon}): {e}")
            results[horizon] = {"error": str(e)}

    return {"predictions": results, "generated_at": str(date.today())}


# ==========================================
# ANALYSIS & ADVISOR
# ==========================================

@router.get("/analysis")
def get_market_analysis():
    """Phân tích thị trường vàng."""
    try:
        from app.services.ai_reasoning.market_analyzer import MarketAnalyzer
        from app.services.feature_engine.feature_builder import FeatureBuilder

        builder = FeatureBuilder()
        df = builder.build_features(source="xau_usd", include_macro=True)

        if df.empty:
            raise HTTPException(404, "Không có dữ liệu để phân tích")

        latest = df.iloc[-1].to_dict()

        trainer = _get_trainer()
        prediction = {}
        if "7d" in trainer.trained_models:
            prediction = trainer.predict(horizon="7d")

        analyzer = MarketAnalyzer()
        analysis = analyzer.analyze(latest, prediction)

        return analysis
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analysis error: {e}")
        raise HTTPException(500, str(e))


@router.get("/advisor")
def get_investment_advice(horizon: str = Query(default="7d")):
    """Lời khuyên đầu tư."""
    try:
        from app.services.advisor.investment_advisor import InvestmentAdvisor

        trainer = _get_trainer()
        if horizon not in trainer.trained_models:
            trainer.train_all(horizon=horizon)

        advisor = InvestmentAdvisor()
        advice = advisor.get_advice(trainer=trainer, horizon=horizon)
        return advice
    except Exception as e:
        logger.error(f"Advisor error: {e}")
        raise HTTPException(500, str(e))


# ==========================================
# TRAINING & DATA COLLECTION
# ==========================================

@router.post("/train")
def train_models(request: TrainRequest):
    """Train/retrain ML models."""
    try:
        trainer = _get_trainer()
        results = trainer.train_all(horizon=request.horizon, source=request.source)

        return TrainResponse(
            status="success",
            horizon=request.horizon,
            metrics=results,
            message=f"Models trained successfully for {request.horizon}",
        )
    except Exception as e:
        logger.error(f"Training error: {e}")
        raise HTTPException(500, str(e))


@router.post("/collect-data")
def collect_data():
    """Thu thập dữ liệu mới."""
    try:
        from app.services.data_collector.data_pipeline import DataPipeline
        pipeline = DataPipeline()
        results = pipeline.run_all()

        return CollectDataResponse(
            status="success",
            results=results,
            message="Data collection completed",
        )
    except Exception as e:
        logger.error(f"Collection error: {e}")
        raise HTTPException(500, str(e))


# ==========================================
# VN GOLD (SJC)
# ==========================================

@router.get("/gold/vn")
def get_vn_gold_analysis():
    """Phân tích giá vàng Việt Nam: SJC thực tế vs quy đổi."""
    try:
        from app.services.models.vn_gold_predictor import VNGoldPredictor
        predictor = VNGoldPredictor()
        return predictor.get_current_analysis()
    except Exception as e:
        logger.error(f"VN gold analysis error: {e}")
        raise HTTPException(500, str(e))


@router.get("/gold/vn/compare")
def compare_vn_gold_prices():
    """So sánh giá vàng tất cả đơn vị (SJC, PNJ, DOJI, ...) từ giavang.org."""
    try:
        from app.services.data_collector.giavang_org_collector import GiavangOrgCollector
        collector = GiavangOrgCollector()
        df = collector.fetch_multi_org_prices()

        if df.empty:
            raise HTTPException(404, "Không lấy được dữ liệu giavang.org")

        orgs = []
        for _, row in df.iterrows():
            orgs.append({
                "organization": row.get("organization", ""),
                "region": row.get("region", ""),
                "buy_price": row.get("buy_price", 0),
                "sell_price": row.get("sell_price", 0),
            })

        return {
            "date": str(df.iloc[0]["date"]),
            "source": "giavang.org",
            "total_records": len(orgs),
            "organizations": orgs,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Compare VN gold error: {e}")
        raise HTTPException(500, str(e))


@router.get("/gold/vn/predict")
def predict_vn_gold(horizon: str = Query(default="7d")):
    """Dự đoán giá SJC từ XAU/USD forecast."""
    try:
        from app.services.models.vn_gold_predictor import VNGoldPredictor

        trainer = _get_trainer()
        if horizon not in trainer.trained_models:
            trainer.train_all(horizon=horizon)

        xau_pred = trainer.predict(horizon=horizon)
        predictor = VNGoldPredictor()
        sjc_result = predictor.predict_sjc_price(xau_pred.get("predicted_price", 0))

        trend_map = {0: "Giảm", 1: "Đi ngang", 2: "Tăng"}
        return {
            "horizon": horizon,
            "xau_usd": {
                "predicted_price": xau_pred.get("predicted_price"),
                "predicted_trend": trend_map.get(xau_pred.get("predicted_trend", 1)),
            },
            "sjc": {
                "buy_predicted": sjc_result["sjc_buy_estimated"],
                "sell_predicted": sjc_result["sjc_sell_estimated"],
                "world_price_vnd": sjc_result["world_price_vnd_per_luong"],
                "premium": sjc_result["premium_vnd"],
                "formula": sjc_result["formula"],
            },
        }
    except Exception as e:
        logger.error(f"VN predict error: {e}")
        raise HTTPException(500, str(e))


# ==========================================
# PREDICTION EXPLANATION (SHAP)
# ==========================================

@router.get("/predictions/{horizon}/explain")
def explain_prediction(horizon: str = "7d"):
    """Giải thích TẠI SAO model dự đoán tăng/giảm (SHAP values)."""
    if horizon not in PREDICTION_HORIZONS:
        raise HTTPException(400, f"Invalid horizon: {horizon}")

    try:
        from app.services.ai_reasoning.prediction_explainer import PredictionExplainer
        from app.services.feature_engine.feature_builder import FeatureBuilder

        trainer = _get_trainer()
        if horizon not in trainer.trained_models:
            trainer.train_all(horizon=horizon)

        # Build features
        builder = FeatureBuilder()
        df = builder.build_features(source="xau_usd", include_macro=True)
        if df.empty:
            raise HTTPException(404, "Khong co du lieu")

        # Get latest features (drop target columns)
        target_cols = [c for c in df.columns if c.startswith("target_")]
        feature_cols = [c for c in df.columns if c not in target_cols and c != "date"]
        X_latest = df[feature_cols].iloc[[-1]].copy()

        # Drop NaN columns
        X_latest = X_latest.dropna(axis=1)

        # Get model
        models = trainer.trained_models.get(horizon, {})
        price_model = models.get("price")

        explainer = PredictionExplainer()
        result = {}

        if price_model:
            # Align features with model
            model_features = price_model.feature_names
            common = [f for f in model_features if f in X_latest.columns]
            X_aligned = X_latest[common]
            result["price_explanation"] = explainer.explain_prediction(
                price_model, X_aligned, top_n=8
            )

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Explanation error: {e}")
        raise HTTPException(500, str(e))


# ==========================================
# V2: BACKTESTING & RISK METRICS
# ==========================================

@router.get("/backtest/metrics")
def get_backtest_metrics(horizon: str = Query(default="7d")):
    """Lấy backtest + risk metrics cho model."""
    if horizon not in PREDICTION_HORIZONS:
        raise HTTPException(400, f"Invalid horizon: {horizon}")

    try:
        from app.services.backtesting.backtester import Backtester
        from app.services.backtesting.risk_metrics import RiskMetrics

        trainer = _get_trainer()
        if horizon not in trainer.trained_models:
            trainer.train_all(horizon=horizon)

        # Use walk-forward validation as proxy backtest
        wf_results = trainer.walk_forward_validate(horizon=horizon)

        if not wf_results:
            return {"error": "Không đủ data cho walk-forward"}

        return {
            "horizon": horizon,
            "n_windows": wf_results["n_windows"],
            "avg_return_mae": wf_results["avg_return_metrics"]["mae"],
            "avg_return_r2": wf_results["avg_return_metrics"]["r2"],
            "avg_trend_accuracy": wf_results["avg_trend_metrics"]["accuracy"],
            "avg_trend_f1": wf_results["avg_trend_metrics"]["f1"],
            "std_return_mae": wf_results["std_return_metrics"]["mae"],
            "windows": wf_results["windows"],
        }
    except Exception as e:
        logger.error(f"Backtest error: {e}")
        raise HTTPException(500, str(e))


@router.get("/walk-forward")
def get_walk_forward(horizon: str = Query(default="7d")):
    """Chạy walk-forward validation và trả kết quả chi tiết."""
    if horizon not in PREDICTION_HORIZONS:
        raise HTTPException(400, f"Invalid horizon: {horizon}")

    try:
        trainer = _get_trainer()
        results = trainer.walk_forward_validate(horizon=horizon)
        return results if results else {"error": "Không đủ data"}
    except Exception as e:
        logger.error(f"Walk-forward error: {e}")
        raise HTTPException(500, str(e))


# ==========================================
# V2: FEAR & GREED + SENTIMENT
# ==========================================

@router.get("/fear-greed")
def get_fear_greed(days: int = Query(default=30, ge=1, le=365)):
    """Lấy Fear & Greed Index."""
    try:
        from app.db.database import get_session_factory

        SessionLocal = get_session_factory()
        db = SessionLocal()
        try:
            from datetime import timedelta
            cutoff = date.today() - timedelta(days=days)
            records = db.query(MacroIndicator).filter(
                MacroIndicator.indicator == "fear_greed",
                MacroIndicator.date >= cutoff,
            ).order_by(MacroIndicator.date.desc()).all()

            if not records:
                # Try fetching fresh data
                from app.services.data_collector.fear_greed_collector import FearGreedCollector
                fg = FearGreedCollector()
                fg.collect_and_store()
                records = db.query(MacroIndicator).filter(
                    MacroIndicator.indicator == "fear_greed",
                    MacroIndicator.date >= cutoff,
                ).order_by(MacroIndicator.date.desc()).all()

            data = [{"date": str(r.date), "value": r.close} for r in records]
            latest = data[0] if data else None

            # Classification
            classification = "N/A"
            if latest:
                v = latest["value"]
                if v <= 25:
                    classification = "Extreme Fear"
                elif v <= 40:
                    classification = "Fear"
                elif v <= 60:
                    classification = "Neutral"
                elif v <= 75:
                    classification = "Greed"
                else:
                    classification = "Extreme Greed"

            return {
                "latest": latest,
                "classification": classification,
                "history": data[:30],  # Last 30 entries
                "total_records": len(data),
            }
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Fear & Greed error: {e}")
        raise HTTPException(500, str(e))


@router.get("/sentiment")
def get_sentiment(days: int = Query(default=7)):
    """Lấy news sentiment summary."""
    try:
        from app.services.data_collector.sentiment_analyzer import SentimentAnalyzer
        analyzer = SentimentAnalyzer()
        daily = analyzer.get_daily_sentiment(days=days)

        # Overall summary
        if daily:
            scores = [v["avg_score"] for v in daily.values()]
            avg = sum(scores) / len(scores) if scores else 0
            overall = "Bullish" if avg > 0.1 else "Bearish" if avg < -0.1 else "Neutral"
        else:
            avg = 0
            overall = "N/A"

        return {
            "overall_sentiment": overall,
            "avg_score": round(avg, 4),
            "daily": daily,
            "period_days": days,
        }
    except Exception as e:
        logger.error(f"Sentiment error: {e}")
        raise HTTPException(500, str(e))


# ==========================================
# V2: MODEL COMPARISON
# ==========================================

@router.get("/models/compare")
def compare_models(horizon: str = Query(default="7d")):
    """So sánh accuracy tất cả models."""
    if horizon not in PREDICTION_HORIZONS:
        raise HTTPException(400, f"Invalid horizon: {horizon}")

    try:
        trainer = _get_trainer()
        if horizon not in trainer.trained_models:
            trainer.train_all(horizon=horizon)

        models = trainer.trained_models.get(horizon, {})
        comparison = []

        for name, model in models.items():
            if model is None:
                continue
            entry = {
                "name": name,
                "type": getattr(model, "model_type", "unknown"),
                "is_trained": getattr(model, "is_trained", False),
            }
            metrics = getattr(model, "train_metrics", {})
            if metrics:
                entry["metrics"] = metrics
            comparison.append(entry)

        return {
            "horizon": horizon,
            "models": comparison,
            "total_models": len(comparison),
        }
    except Exception as e:
        logger.error(f"Model compare error: {e}")
        raise HTTPException(500, str(e))


# ==========================================
# SCHEDULER MANAGEMENT
# ==========================================

@router.get("/scheduler/status")
def get_scheduler_status_api():
    """Xem trạng thái scheduler, danh sách jobs, next run times."""
    logger.info("GET /scheduler/status")
    from app.scheduler import get_scheduler_status
    return get_scheduler_status()


@router.post("/scheduler/trigger-collect")
def trigger_collect_now_api():
    """Trigger thu thập dữ liệu ngay lập tức (không đợi schedule)."""
    logger.info("POST /scheduler/trigger-collect")
    from app.scheduler import trigger_collect_now
    result = trigger_collect_now()
    return result
