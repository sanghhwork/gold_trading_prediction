"""
Gold Predictor - Logging Utility
Sử dụng loguru cho logging có cấu trúc, dễ trace.

Lưu ý bảo mật:
- KHÔNG log biến môi trường (.env)
- KHÔNG log thông tin database credentials
- KHÔNG log API keys, tokens, secrets
"""

import sys
from pathlib import Path
from loguru import logger

# Xóa default handler
logger.remove()

# ===== Console Handler =====
# Format rõ ràng, có màu sắc, dễ đọc khi dev
logger.add(
    sys.stderr,
    format=(
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    ),
    level="DEBUG",
    colorize=True,
)

# ===== File Handler =====
# Log vào file, rotate hàng ngày, giữ 30 ngày
LOG_DIR = Path(__file__).parent.parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

logger.add(
    LOG_DIR / "gold_predictor_{time:YYYY-MM-DD}.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
    level="INFO",
    rotation="1 day",
    retention="30 days",
    compression="zip",
    encoding="utf-8",
)

# ===== Error-only File Handler =====
# File riêng cho errors, dễ trace lỗi
logger.add(
    LOG_DIR / "errors_{time:YYYY-MM-DD}.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}\n{exception}",
    level="ERROR",
    rotation="1 day",
    retention="60 days",
    compression="zip",
    encoding="utf-8",
)


def get_logger(name: str = "gold_predictor"):
    """
    Lấy logger instance với context name.
    
    Usage:
        from app.utils.logger import get_logger
        logger = get_logger(__name__)
        logger.info("Message here")
    
    Điểm mở rộng tương lai:
    - Thêm structured logging (JSON format) cho production
    - Thêm log shipping tới ELK/Grafana
    """
    return logger.bind(name=name)
