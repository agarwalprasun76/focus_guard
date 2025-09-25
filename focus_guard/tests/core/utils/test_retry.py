"""
Tests for the retry utility module.
"""
import asyncio
import logging
import pytest
from unittest.mock import patch, MagicMock, call

from focus_guard.core.utils.retry import retry, async_retry

# Test logger
logger = logging.getLogger(__name__)


def test_retry_success():
    """Test that retry succeeds on first attempt."""
    mock_func = MagicMock(return_value="success")
    decorated = retry(max_attempts=3)(mock_func)
    
    result = decorated()
    
    assert result == "success"
    mock_func.assert_called_once()


def test_retry_failure_then_success():
    """Test that retry succeeds after some failures."""
    mock_func = MagicMock()
    mock_func.side_effect = [ValueError("Failed"), "success"]
    
    decorated = retry(max_attempts=3, logger=logger)(mock_func)
    
    result = decorated()
    assert result == "success"
    assert mock_func.call_count == 2


def test_retry_exhausted():
    """Test that retry gives up after max attempts."""
    mock_func = MagicMock()
    mock_func.side_effect = ValueError("Failed")
    
    decorated = retry(max_attempts=3, logger=logger)(mock_func)
    
    with pytest.raises(ValueError, match="Failed"):
        decorated()
    
    assert mock_func.call_count == 3


def test_retry_specific_exceptions():
    """Test that retry only catches specified exceptions."""
    mock_func = MagicMock()
    mock_func.side_effect = ValueError("Failed")
    
    decorated = retry(
        max_attempts=2,
        exceptions=TypeError,
        logger=logger
    )(mock_func)
    
    with pytest.raises(ValueError):
        decorated()
    
    mock_func.assert_called_once()


@pytest.mark.asyncio
async def test_async_retry_success():
    """Test that async_retry succeeds on first attempt."""
    async def mock_coro():
        return "success"
        
    mock_func = MagicMock(side_effect=mock_coro)
    decorated = async_retry(max_attempts=3)(mock_func)
    
    result = await decorated()
    
    assert result == "success"
    mock_func.assert_called_once()


@pytest.mark.asyncio
async def test_async_retry_failure_then_success():
    """Test that async_retry succeeds after some failures."""
    call_count = 0
    
    async def mock_async_func():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise ValueError("Failed")
        return "success"
    
    decorated = async_retry(max_attempts=3, logger=logger)(mock_async_func)
    
    result = await decorated()
    assert result == "success"
    assert call_count == 2


def test_retry_with_backoff():
    """Test that retry uses exponential backoff."""
    mock_func = MagicMock()
    mock_func.side_effect = [ValueError("Failed"), "success"]
    
    with patch('time.sleep') as mock_sleep:
        decorated = retry(
            max_attempts=2,
            initial_delay=0.1,
            backoff_factor=2,
            logger=logger
        )(mock_func)
        
        decorated()
        
        # Should sleep with exponential backoff
        mock_sleep.assert_called_once_with(0.1)  # 0.1s initial delay


def test_retry_logging(caplog):
    """Test that retry logs attempts and failures."""
    mock_func = MagicMock()
    mock_func.side_effect = [ValueError("Failed"), "success"]
    
    with caplog.at_level(logging.WARNING):
        decorated = retry(
            max_attempts=2,
            initial_delay=0.1,
            logger=logger
        )(mock_func)
        
        result = decorated()
        
    assert result == "success"
    assert "Attempt 1/2 failed: Failed" in caplog.text
