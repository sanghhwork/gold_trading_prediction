"""
Gold Predictor - Constants
Hằng số sử dụng trong toàn bộ ứng dụng.

Điểm mở rộng tương lai:
- Thêm tickers cho crypto gold tokens
- Thêm currencies khác (EUR, GBP, JPY)
"""

# ===== yfinance Tickers =====
# Vàng
TICKER_XAU_USD = "GC=F"           # Gold Futures (XAU/USD)
TICKER_XAU_USD_SPOT = "XAUUSD=X"  # Gold Spot price

# Macro Indicators
TICKER_DXY = "DX-Y.NYB"           # US Dollar Index
TICKER_USD_VND = "VND=X"          # USD/VND exchange rate
TICKER_OIL_WTI = "CL=F"          # Crude Oil WTI Futures
TICKER_US_10Y = "^TNX"            # US 10-Year Treasury Yield
TICKER_SP500 = "^GSPC"            # S&P 500 Index
TICKER_GLD = "GLD"                # SPDR Gold Shares ETF (flows proxy)

# Tất cả tickers cần thu thập từ yfinance
ALL_YFINANCE_TICKERS = {
    "xau_usd": TICKER_XAU_USD,
    "dxy": TICKER_DXY,
    "usd_vnd": TICKER_USD_VND,
    "oil_wti": TICKER_OIL_WTI,
    "us_10y": TICKER_US_10Y,
    "sp500": TICKER_SP500,
    "gld_etf": TICKER_GLD,
}

# ===== SJC Scraping =====
SJC_URL = "https://sjc.com.vn/xml/tygiavang.xml"
SJC_BACKUP_URL = "https://www.sjc.com.vn"

# ===== News Sources =====
NEWS_SOURCES = {
    "cafef": "https://cafef.vn/vang.chn",
    "kitco": "https://www.kitco.com/news/gold",
}

# ===== Technical Indicators Parameters =====
# Moving Averages
SMA_PERIODS = [20, 50, 200]
EMA_PERIODS = [12, 26]

# RSI
RSI_PERIOD = 14

# MACD
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

# Bollinger Bands
BB_PERIOD = 20
BB_STD = 2

# ATR
ATR_PERIOD = 14

# Stochastic
STOCH_K_PERIOD = 14
STOCH_D_PERIOD = 3

# Williams %R
WILLIAMS_PERIOD = 14

# ===== Lag Features =====
LAG_DAYS = [1, 5, 10, 20]
RETURN_PERIODS = [1, 5, 20]

# ===== ML Model Parameters =====
# Walk-forward validation
TRAIN_WINDOW_DAYS = 252 * 3    # 3 năm trading days
TEST_WINDOW_DAYS = 252          # 1 năm trading days
WALK_FORWARD_STEP = 21          # Bước nhảy 1 tháng (21 trading days)

# LSTM
LSTM_SEQUENCE_LENGTH = 60       # 60 ngày lookback
LSTM_EPOCHS = 100
LSTM_BATCH_SIZE = 32

# XGBoost defaults
XGBOOST_N_ESTIMATORS = 500
XGBOOST_MAX_DEPTH = 6
XGBOOST_LEARNING_RATE = 0.05

# ===== Prediction Horizons =====
PREDICTION_HORIZONS = {
    "1d": 1,     # 1 ngày
    "7d": 7,     # 1 tuần
    "30d": 30,   # 1 tháng
}

# ===== Trend Classification =====
TREND_THRESHOLD_UP = 0.005     # >0.5% = Tăng (legacy, dùng cho backward compat)
TREND_THRESHOLD_DOWN = -0.005  # <-0.5% = Giảm

# Dynamic thresholds: tỷ lệ với horizon — chính xác hơn cho mỗi timeframe
DYNAMIC_TREND_THRESHOLDS = {
    "1d": 0.005,   # ±0.5% cho 1 ngày
    "7d": 0.01,    # ±1.0% cho 1 tuần
    "30d": 0.02,   # ±2.0% cho 1 tháng
}

# ===== Walk-Forward Validation =====
EMBARGO_DAYS = 5  # Gap giữa train/test để tránh autocorrelation

TREND_LABELS = {
    0: "Giảm",
    1: "Sideway",
    2: "Tăng",
}

# ===== Volatility Classification =====
VOLATILITY_LABELS = {
    0: "Thấp",
    1: "Trung bình",
    2: "Cao",
}

# ===== Investment Advice Signals =====
SIGNAL_BUY = "BUY"
SIGNAL_SELL = "SELL"
SIGNAL_HOLD = "HOLD"
SIGNAL_STRONG_BUY = "STRONG_BUY"
SIGNAL_STRONG_SELL = "STRONG_SELL"

# ===== Risk Levels =====
RISK_LOW = "LOW"
RISK_MEDIUM = "MEDIUM"
RISK_HIGH = "HIGH"
RISK_VERY_HIGH = "VERY_HIGH"

# ===== API =====
API_V1_PREFIX = "/api/v1"

# ===== Date Formats =====
DATE_FORMAT = "%Y-%m-%d"
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
