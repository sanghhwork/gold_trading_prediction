"""
Gold Predictor - Gemini AI Client
Wrapper cho Google Gemini API với fallback khi không có API key.

Strategy:
- Có API key → Gọi Gemini API (advanced analysis)
- Không có key → Rule-based analysis (từ ML models + TA)

Điểm mở rộng tương lai:
- Thêm DeepSeek/GPT-4o backup
- Thêm response caching
- Thêm prompt templates management
"""

from typing import Optional

from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

_client = None
_is_available = None


def is_gemini_available() -> bool:
    """Kiểm tra Gemini API có sẵn sàng không."""
    global _is_available
    if _is_available is not None:
        return _is_available

    settings = get_settings()
    if not settings.gemini_api_key or settings.gemini_api_key == "your_gemini_api_key_here":
        logger.info("Gemini API key chưa cấu hình → sử dụng rule-based analysis")
        _is_available = False
        return False

    try:
        import google.generativeai as genai
        genai.configure(api_key=settings.gemini_api_key)
        # Quick test
        model = genai.GenerativeModel("gemini-2.0-flash")
        model.count_tokens("test")
        _is_available = True
        logger.info("Gemini API sẵn sàng")
        return True
    except Exception as e:
        logger.warning(f"Gemini API không khả dụng: {e}")
        _is_available = False
        return False


def get_gemini_client():
    """Lấy Gemini model instance."""
    global _client
    if _client is not None:
        return _client

    if not is_gemini_available():
        return None

    import google.generativeai as genai
    settings = get_settings()
    genai.configure(api_key=settings.gemini_api_key)
    _client = genai.GenerativeModel("gemini-2.0-flash")
    return _client


async def ask_gemini(prompt: str, max_tokens: int = 2048) -> Optional[str]:
    """
    Gửi prompt tới Gemini và nhận response.
    Returns None nếu không khả dụng hoặc lỗi.
    """
    client = get_gemini_client()
    if client is None:
        return None

    try:
        response = client.generate_content(
            prompt,
            generation_config={
                "max_output_tokens": max_tokens,
                "temperature": 0.3,
            },
        )
        return response.text
    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        return None
