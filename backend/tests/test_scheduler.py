"""
Tests for Scheduler module.
Test startup catch-up logic, trading day calculation, concurrent prevention.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from datetime import date, timedelta
from unittest.mock import patch, MagicMock


class TestGetLastTradingDay:
    """Test _get_last_trading_day() — skip weekend logic."""

    def test_weekday_returns_today(self):
        """Ngày trong tuần → return chính nó."""
        from app.scheduler import _get_last_trading_day
        
        # Monday = 0
        with patch('app.scheduler.date') as mock_date:
            mock_date.today.return_value = date(2026, 3, 23)  # Monday
            mock_date.side_effect = lambda *args, **kw: date(*args, **kw)
            result = _get_last_trading_day()
            assert result == date(2026, 3, 23)

    def test_saturday_returns_friday(self):
        """Saturday → return Friday."""
        from app.scheduler import _get_last_trading_day
        
        with patch('app.scheduler.date') as mock_date:
            mock_date.today.return_value = date(2026, 3, 28)  # Saturday
            mock_date.side_effect = lambda *args, **kw: date(*args, **kw)
            result = _get_last_trading_day()
            assert result == date(2026, 3, 27)  # Friday

    def test_sunday_returns_friday(self):
        """Sunday → return Friday."""
        from app.scheduler import _get_last_trading_day
        
        with patch('app.scheduler.date') as mock_date:
            mock_date.today.return_value = date(2026, 3, 29)  # Sunday
            mock_date.side_effect = lambda *args, **kw: date(*args, **kw)
            result = _get_last_trading_day()
            assert result == date(2026, 3, 27)  # Friday

    def test_friday_returns_friday(self):
        """Friday → return chính nó."""
        from app.scheduler import _get_last_trading_day
        
        with patch('app.scheduler.date') as mock_date:
            mock_date.today.return_value = date(2026, 3, 27)  # Friday
            mock_date.side_effect = lambda *args, **kw: date(*args, **kw)
            result = _get_last_trading_day()
            assert result == date(2026, 3, 27)


class TestShouldCollectOnStartup:
    """Test _should_collect_on_startup() logic."""

    @patch('app.scheduler._get_last_trading_day')
    @patch('app.db.database.get_session_factory')
    def test_empty_db_returns_true(self, mock_factory, mock_trading_day):
        """DB trống → cần collect."""
        from app.scheduler import _should_collect_on_startup
        
        mock_session = MagicMock()
        mock_session.query.return_value.filter_by.return_value.scalar.return_value = None
        mock_factory.return_value.return_value = mock_session
        
        assert _should_collect_on_startup() is True

    @patch('app.scheduler._get_last_trading_day')
    @patch('app.db.database.get_session_factory')
    def test_old_data_returns_true(self, mock_factory, mock_trading_day):
        """Data cũ hơn 1 ngày giao dịch → cần collect."""
        from app.scheduler import _should_collect_on_startup
        
        mock_session = MagicMock()
        mock_session.query.return_value.filter_by.return_value.scalar.return_value = date(2026, 3, 20)
        mock_factory.return_value.return_value = mock_session
        mock_trading_day.return_value = date(2026, 3, 25)
        
        assert _should_collect_on_startup() is True

    @patch('app.scheduler._get_last_trading_day')
    @patch('app.db.database.get_session_factory')
    def test_fresh_data_returns_false(self, mock_factory, mock_trading_day):
        """Data mới → không cần collect."""
        from app.scheduler import _should_collect_on_startup
        
        mock_session = MagicMock()
        mock_session.query.return_value.filter_by.return_value.scalar.return_value = date(2026, 3, 25)
        mock_factory.return_value.return_value = mock_session
        mock_trading_day.return_value = date(2026, 3, 25)
        
        assert _should_collect_on_startup() is False

    @patch('app.db.database.get_session_factory')
    def test_db_error_returns_false(self, mock_factory):
        """DB lỗi → an toàn, không collect."""
        from app.scheduler import _should_collect_on_startup
        
        mock_factory.side_effect = Exception("DB connection failed")
        
        assert _should_collect_on_startup() is False


class TestConcurrentCollectionPrevention:
    """Test _is_collecting flag prevent concurrent runs."""

    def test_concurrent_skip(self):
        """Khi _is_collecting=True → skip job mới."""
        import app.scheduler as scheduler_module
        
        # Set flag
        original = scheduler_module._is_collecting
        scheduler_module._is_collecting = True
        
        try:
            # Job should return immediately without doing anything
            scheduler_module._job_collect_data()
            # If we got here without error, it means it skipped correctly
            assert scheduler_module._is_collecting is True
        finally:
            scheduler_module._is_collecting = original


class TestTriggerCollectNow:
    """Test trigger_collect_now() manual trigger."""

    def test_returns_skipped_when_collecting(self):
        """Khi đang collect → return skipped."""
        import app.scheduler as scheduler_module
        
        original = scheduler_module._is_collecting
        scheduler_module._is_collecting = True
        
        try:
            result = scheduler_module.trigger_collect_now()
            assert result["status"] == "skipped"
        finally:
            scheduler_module._is_collecting = original


class TestSchedulerConfig:
    """Test scheduler config integration."""

    def test_scheduler_enabled_default(self):
        """Default scheduler_enabled = True."""
        from app.config import Settings
        settings = Settings()
        assert settings.scheduler_enabled is True

    def test_scheduler_status_when_not_started(self):
        """Scheduler chưa start → running=False."""
        import app.scheduler as scheduler_module
        
        original = scheduler_module._scheduler
        scheduler_module._scheduler = None
        
        try:
            status = scheduler_module.get_scheduler_status()
            assert status["running"] is False
        finally:
            scheduler_module._scheduler = original


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
