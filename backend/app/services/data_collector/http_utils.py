"""
Gold Predictor - HTTP Utilities (Resilience Layer)
Cung cấp ResilientSession với retry logic, User-Agent rotation, rate limiting.

Module này tách riêng logic HTTP resilience để:
- Tất cả collectors import và sử dụng chung
- Dễ test và dễ mở rộng (thêm proxy rotation sau)
- Giảm code trùng lặp giữa các collectors

Điểm mở rộng tương lai:
- Thêm proxy rotation (khi có budget)
- Thêm request caching (cho development)
- Thêm circuit breaker pattern
"""

import random
import time
from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.utils.logger import get_logger

logger = get_logger(__name__)

# ===== User-Agent Pool =====
# Pool 12 UA strings đa dạng (Chrome, Firefox, Safari, Edge) trên nhiều OS
# Dễ thêm/bớt: chỉ cần append vào list
USER_AGENT_POOL = [
    # Chrome - Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    # Chrome - macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    # Firefox - Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
    # Firefox - macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:123.0) Gecko/20100101 Firefox/123.0",
    # Safari - macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    # Edge - Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
    # Chrome - Linux
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
]


# ===== Error Categories =====
# Phân loại lỗi HTTP để log rõ ràng và xử lý phù hợp
ERROR_CATEGORIES = {
    403: "BLOCKED",
    429: "RATE_LIMIT",
    503: "SERVICE_UNAVAILABLE",
    502: "BAD_GATEWAY",
    404: "NOT_FOUND",
    500: "SERVER_ERROR",
}


def get_random_user_agent() -> str:
    """Lấy ngẫu nhiên 1 User-Agent từ pool."""
    return random.choice(USER_AGENT_POOL)


def categorize_error(status_code: Optional[int] = None, exception: Optional[Exception] = None) -> str:
    """
    Phân loại lỗi HTTP/Network thành category rõ ràng cho logging.
    
    Returns: "BLOCKED", "RATE_LIMIT", "TIMEOUT", "NETWORK", "NOT_FOUND", "SERVER_ERROR", "UNKNOWN"
    """
    if status_code and status_code in ERROR_CATEGORIES:
        return ERROR_CATEGORIES[status_code]
    
    if exception:
        exc_str = str(type(exception).__name__).lower()
        if "timeout" in exc_str or "timeout" in str(exception).lower():
            return "TIMEOUT"
        if "connection" in exc_str or "connection" in str(exception).lower():
            return "NETWORK"
        if "ssl" in exc_str:
            return "NETWORK"
    
    if status_code and 400 <= status_code < 500:
        return "CLIENT_ERROR"
    if status_code and status_code >= 500:
        return "SERVER_ERROR"
    
    return "UNKNOWN"


class ResilientSession:
    """
    Wrapper requests.Session với retry logic, UA rotation, rate limiting.
    
    Features:
    - Retry với exponential backoff (configurable)
    - User-Agent rotation mỗi request
    - Random delay giữa các requests (anti-fingerprint)
    - Error categorization cho logging rõ ràng
    - Reuse connection (keep-alive) qua requests.Session
    
    Điểm mở rộng:
    - Thêm proxy_list parameter cho proxy rotation
    - Thêm cache_ttl cho response caching
    """

    def __init__(
        self,
        max_retries: int = 3,
        retry_delay: float = 2.0,
        min_request_delay: float = 1.0,
        max_request_delay: float = 3.0,
        timeout: int = 15,
    ):
        """
        Args:
            max_retries: Số lần retry tối đa khi gặp lỗi
            retry_delay: Delay base cho exponential backoff (seconds)
            min_request_delay: Delay tối thiểu giữa các requests (seconds)
            max_request_delay: Delay tối đa giữa các requests (seconds)
            timeout: Timeout mặc định cho mỗi request (seconds)
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.min_request_delay = min_request_delay
        self.max_request_delay = max_request_delay
        self.timeout = timeout
        self._session = self._create_session()
        self._last_request_time = 0.0
        self.logger = get_logger("resilient_session")

    def _create_session(self) -> requests.Session:
        """Tạo requests.Session với retry adapter cơ bản."""
        session = requests.Session()
        
        # urllib3 retry cho connection-level errors (DNS, connection refused)
        # Application-level retry (HTTP 403, 429) handled bởi logic trong get/post
        retry_strategy = Retry(
            total=2,
            backoff_factor=1,
            status_forcelist=[502, 503, 504],
            allowed_methods=["GET", "POST"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session

    def _get_headers(self, extra_headers: Optional[dict] = None) -> dict:
        """Tạo headers với User-Agent ngẫu nhiên."""
        headers = {
            "User-Agent": get_random_user_agent(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
        }
        if extra_headers:
            headers.update(extra_headers)
        return headers

    def _wait_between_requests(self):
        """Đợi ngẫu nhiên giữa các requests để tránh bị fingerprint."""
        now = time.time()
        elapsed = now - self._last_request_time
        min_wait = self.min_request_delay
        
        if elapsed < min_wait:
            wait = random.uniform(min_wait - elapsed, self.max_request_delay - elapsed)
            if wait > 0:
                time.sleep(wait)
        
        self._last_request_time = time.time()

    def get(
        self,
        url: str,
        params: Optional[dict] = None,
        headers: Optional[dict] = None,
        timeout: Optional[int] = None,
        **kwargs,
    ) -> requests.Response:
        """
        GET request với retry logic và UA rotation.
        
        Raises:
            requests.RequestException: Nếu tất cả retries đều fail
        """
        return self._request("GET", url, params=params, headers=headers, timeout=timeout, **kwargs)

    def post(
        self,
        url: str,
        data: Optional[dict] = None,
        json: Optional[dict] = None,
        headers: Optional[dict] = None,
        timeout: Optional[int] = None,
        **kwargs,
    ) -> requests.Response:
        """
        POST request với retry logic và UA rotation.
        
        Raises:
            requests.RequestException: Nếu tất cả retries đều fail
        """
        return self._request("POST", url, data=data, json=json, headers=headers, timeout=timeout, **kwargs)

    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        """
        Core request method với retry + exponential backoff.
        
        Flow:
        1. Wait between requests (rate limiting)
        2. Set random User-Agent
        3. Execute request
        4. If fail → categorize error → retry with backoff
        5. After max retries → raise last exception
        """
        timeout = kwargs.pop("timeout", None) or self.timeout
        extra_headers = kwargs.pop("headers", None)
        
        last_exception = None
        
        for attempt in range(1, self.max_retries + 1):
            try:
                # Rate limiting
                self._wait_between_requests()
                
                # Random UA mỗi attempt
                request_headers = self._get_headers(extra_headers)
                
                # Execute request
                response = self._session.request(
                    method,
                    url,
                    headers=request_headers,
                    timeout=timeout,
                    **kwargs,
                )
                
                # Check for blocking/rate-limit responses
                if response.status_code in (403, 429):
                    error_cat = categorize_error(status_code=response.status_code)
                    backoff = self.retry_delay * (2 ** (attempt - 1))
                    
                    if attempt < self.max_retries:
                        self.logger.warning(
                            f"[{error_cat}] [{attempt}/{self.max_retries}] "
                            f"{method} {url} → HTTP {response.status_code}, "
                            f"retry sau {backoff:.1f}s..."
                        )
                        time.sleep(backoff)
                        continue
                    else:
                        self.logger.error(
                            f"[{error_cat}] [{attempt}/{self.max_retries}] "
                            f"{method} {url} → HTTP {response.status_code}, "
                            f"hết retry"
                        )
                        response.raise_for_status()
                
                # Success hoặc lỗi không retry được (404, 500, etc.)
                return response
                
            except requests.RequestException as e:
                last_exception = e
                error_cat = categorize_error(exception=e)
                backoff = self.retry_delay * (2 ** (attempt - 1))
                
                if attempt < self.max_retries:
                    self.logger.warning(
                        f"[{error_cat}] [{attempt}/{self.max_retries}] "
                        f"{method} {url} → {type(e).__name__}: {e}, "
                        f"retry sau {backoff:.1f}s..."
                    )
                    time.sleep(backoff)
                else:
                    self.logger.error(
                        f"[{error_cat}] [{attempt}/{self.max_retries}] "
                        f"{method} {url} → {type(e).__name__}: {e}, "
                        f"hết retry"
                    )
        
        # Tất cả retries fail
        raise last_exception

    def close(self):
        """Đóng session và giải phóng connections."""
        self._session.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
