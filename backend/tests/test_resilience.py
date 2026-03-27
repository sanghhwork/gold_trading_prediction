"""
Tests cho Data Collectors V2 (Resilience Layer).
Test ResilientSession, User-Agent rotation, error categorization, fallback chains.
"""

import sys
import os
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.data_collector.http_utils import (
    ResilientSession,
    categorize_error,
    get_random_user_agent,
    USER_AGENT_POOL,
)
import requests


class TestResilienceLayer:
    """Test cơ bản cho http_utils.py."""

    def test_random_user_agent(self):
        """User agent lấy ra phải nằm trong pool."""
        ua = get_random_user_agent()
        assert ua in USER_AGENT_POOL

    def test_categorize_error(self):
        """Phân loại lỗi chính xác."""
        assert categorize_error(status_code=403) == "BLOCKED"
        assert categorize_error(status_code=429) == "RATE_LIMIT"
        assert categorize_error(status_code=500) == "SERVER_ERROR"
        assert categorize_error(status_code=404) == "NOT_FOUND"
        
        # Test exception string
        assert categorize_error(exception=requests.exceptions.Timeout()) == "TIMEOUT"
        assert categorize_error(exception=requests.exceptions.ConnectionError()) == "NETWORK"

    @patch('time.sleep', return_value=None)
    def test_resilient_session_retry(self, mock_sleep):
        """Test cơ chế retry dựa trên Mocking responses."""
        with ResilientSession(max_retries=3, retry_delay=0.1) as session:
            # Mock requests.Session.request
            mock_request = MagicMock()
            
            # Response mock: lần 1-2 báo lỗi 403, lần 3 báo 200
            resp_403 = MagicMock(status_code=403)
            # Không cho raise_for_status lỗi 403
            # Response.raise_for_status không có mặc định trên mock đơn giản,
            # Tuy nhiên mock_request trả về resp_403
            resp_200 = MagicMock(status_code=200)
            mock_request.side_effect = [resp_403, resp_403, resp_200]
            
            session._session.request = mock_request
            
            response = session.get("http://example.com")
            
            # Phải gọi request 3 lần
            assert mock_request.call_count == 3
            assert response.status_code == 200


class TestFallbackChains:
    """Test fallback logic của các Collector."""

    @patch('app.services.data_collector.xau_collector.XAUCollector._fetch_alpha_vantage')
    @patch('app.services.data_collector.xau_collector.XAUCollector._fetch_yfinance')
    def test_xau_fallback_chain(self, mock_yfinance, mock_av):
        """
        Nếu yfinance fail (trả về None / DataFrame rỗng), 
        XAUCollector phải gọi sang alpha_vantage.
        """
        import pandas as pd
        from app.services.data_collector.xau_collector import XAUCollector
        
        collector = XAUCollector()
        # Không có last_date -> sẽ gọi db... Để tránh lỗi DB, mock get_last_date_in_db
        collector.get_last_date_in_db = MagicMock(return_value=None)
        
        # Mock yfinance fail
        mock_yfinance.return_value = pd.DataFrame()
        # Mock av thành công
        mock_av.return_value = pd.DataFrame([{"date": "2024-01-01", "close": 2000}])
        
        df = collector.fetch_data()
        
        # Kiểm tra workflow
        mock_yfinance.assert_called_once()
        mock_av.assert_called_once()
        assert not df.empty
        assert df.iloc[0]["close"] == 2000

    @patch('app.services.data_collector.sjc_collector.SJCCollector._fetch_vang_today')
    @patch('app.services.data_collector.sjc_collector.SJCCollector._fetch_giavang_net')
    @patch('app.services.data_collector.sjc_collector.SJCCollector._fetch_sjc_api')
    def test_sjc_fallback_chain(self, mock_sjc, mock_giavang, mock_vangtoday):
        """
        Nếu sjc.com.vn và giavang.net fail, 
        SJCCollector phải gọi vang.today
        """
        from app.services.data_collector.sjc_collector import SJCCollector
        
        collector = SJCCollector()
        
        # Mock fails
        mock_sjc.return_value = None
        mock_giavang.return_value = None
        
        # Mock success
        mock_vangtoday.return_value = {
            "date": "2024-01-01",
            "source": "sjc",
            "buy_price": 79000000,
            "sell_price": 81000000,
            "close": 81000000
        }
        
        df = collector.fetch_data()
        
        mock_sjc.assert_called_once()
        mock_giavang.assert_called_once()
        mock_vangtoday.assert_called_once()
        
        assert not df.empty
        assert df.iloc[0]["buy_price"] == 79000000

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
