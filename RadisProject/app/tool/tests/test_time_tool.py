"""Tests for TimeTool functionality."""
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
import datetime
import time
from typing import Dict, Any
import socket

from app.tool.time_tool import TimeTool, NTPLIB_AVAILABLE
from app.tool.base import BaseTool

@pytest.fixture
def time_tool():
    """Fixture providing a TimeTool instance."""
    tool = TimeTool()
    yield tool
    asyncio.run(tool.cleanup())

@pytest.fixture
def mock_ntp_response():
    """Fixture providing a mock NTP response."""
    response = MagicMock()
    response.tx_time = time.time()  # Current time
    response.delay = 0.05  # 50ms delay
    response.stratum = 2
    response.precision = -20  # ~1us precision
    return response

@pytest.fixture
def mock_web_response():
    """Fixture for mock web response with time text."""
    return {
        "status": 200,
        "text": AsyncMock(return_value="&lt;div id='time_display'&gt;12:34:56&lt;/div&gt;")
    }

@pytest.mark.asyncio
async def test_ntp_time_fetching_success(time_tool, mock_ntp_response):
    """Test successful NTP time fetching."""
    with patch('ntplib.NTPClient') as mock_ntp:
        mock_instance = mock_ntp.return_value
        mock_instance.request.return_value = mock_ntp_response
        
        result = await time_tool._get_ntp_time()
        
        assert result["status"] == "success"
        assert "ntp_time" in result
        assert "offset_seconds" in result
        assert isinstance(result["delay_ms"], float)
        assert time_tool._last_ntp_time == mock_ntp_response.tx_time
        assert time_tool._time_offset == result["offset_seconds"]

@pytest.mark.asyncio
async def test_ntp_time_fetching_error(time_tool):
    """Test NTP time fetching error handling."""
    with patch('ntplib.NTPClient') as mock_ntp:
        mock_instance = mock_ntp.return_value
        mock_instance.request.side_effect = socket.gaierror("DNS failure")
        
        result = await time_tool._get_ntp_time(server="nonexistent.ntp.org")
        
        assert result["status"] == "error"
        assert "DNS failure" in result["error"]
        assert time_tool._last_ntp_time is None
        assert time_tool._time_offset == 0

@pytest.mark.skipif(not NTPLIB_AVAILABLE, reason="ntplib not available")
@pytest.mark.asyncio
async def test_ntp_without_mocking(time_tool):
    """Test NTP function works with real ntplib (no mocking)."""
    # This will actually try to contact pool.ntp.org
    result = await time_tool._get_ntp_time(timeout=1)
    
    if result["status"] == "success":
        assert isinstance(result["ntp_time"], str)
        assert isinstance(result["offset_seconds"], float)
    else:
        # Network issues are expected in some test environments
        assert "error" in result

@pytest.mark.asyncio
async def test_web_time_fetching_success(time_tool, mock_web_response):
    """Test successful web time fetching."""
    mock_session = AsyncMock()
    mock_session.get.return_value.__aenter__.return_value = mock_web_response
    
    with patch('aiohttp.ClientSession', return_value=mock_session):
        result = await time_tool._get_web_time()
        
        assert result["status"] == "success"
        assert result["sources_succeeded"] > 0
        assert len(result["source_results"]) == len(time_tool.WEB_TIME_SOURCES)
        assert time_tool._last_web_time is not None
        assert time_tool._web_session is mock_session

@pytest.mark.asyncio
async def test_web_time_fetching_error(time_tool):
    """Test web time fetching error handling."""
    mock_session = AsyncMock()
    mock_session.get.side_effect = aiohttp.ClientError("Connection error")
    
    with patch('aiohttp.ClientSession', return_value=mock_session):
        result = await time_tool._get_web_time()
        
        assert result["status"] == "error"
        assert result["sources_succeeded"] == 0
        assert all(r["status"] == "error" for r in result["source_results"])
        assert time_tool._last_web_time is None

@pytest.mark.asyncio
async def test_calibration(time_tool, mock_ntp_response):
    """Test time calibration functionality."""
    with patch('ntplib.NTPClient') as mock_ntp, \
         patch('aiohttp.ClientSession') as mock_session:
        
        # Configure mocks
        mock_ntp_instance = mock_ntp.return_value
        mock_ntp_instance.request.return_value = mock_ntp_response
        
        mock_session_instance = mock_session.return_value
        mock_session_instance.get.return_value.__aenter__.return_value = {
            "status": 200,
            "text": AsyncMock(return_value="&lt;span id='ct'&gt;12:34:56&lt;/span&gt;")
        }
        
        # Test calibration with multiple sources
        result = await time_tool._calibrate_time(use_multiple_sources=True)
        
        assert result["status"] == "success"
        assert result["ntp_sources_succeeded"] == 1  # We only mocked one response
        assert result["web_result"]["status"] == "success"
        assert isinstance(result["avg_offset_seconds"], float)
        assert time_tool._precision is not None
        assert result["system_clock_accurate"] in [True, False]

@pytest.mark.asyncio
async def test_run_actions(time_tool, mock_ntp_response, mock_web_response):
    """Test all run() action types."""
    with patch('ntplib.NTPClient') as mock_ntp, \
         patch('aiohttp.ClientSession') as mock_session:
        
        # Configure mocks
        mock_ntp_instance = mock_ntp.return_value
        mock_ntp_instance.request.return_value = mock_ntp_response
        
        mock_session_instance = mock_session.return_value
        mock_session_instance.get.return_value.__aenter__.return_value = mock_web_response
        
        # Test NTP action
        ntp_result = await time_tool.run(action="ntp")
        assert ntp_result["status"] == "success"
        
        # Test web action
        web_result = await time_tool.run(action="web")
        assert web_result["status"] == "success"
        
        # Test calibrate action
        cal_result = await time_tool.run(action="calibrate")
        assert cal_result["status"] == "success"
        
        # Test system action
        sys_result = await time_tool.run(action="system")
        assert sys_result["status"] == "success"
        assert sys_result["offset_applied"]

        # Test invalid action
        bad_result = await time_tool.run(action="invalid")
        assert bad_result["status"] == "error"

@pytest.mark.asyncio
async def test_reset_method(time_tool, mock_ntp_response):
    """Test reset() method functionality."""
    # First set some state
    with patch('ntplib.NTPClient') as mock_ntp:
        mock_ntp_instance = mock_ntp.return_value
        mock_ntp_instance.request.return_value = mock_ntp_response
        
        await time_tool._get_ntp_time()
        assert time_tool._last_ntp_time is not None
        assert time_tool._time_offset != 0
        
        # Test reset
        await time_tool.reset()
        
        assert time_tool._last_ntp_time is None
        assert time_tool._time_offset == 0
        assert time_tool._precision is None
        assert time_tool._web_session is None

@pytest.mark.asyncio
async def test_state_management(time_tool):
    """Test internal state management."""
    assert time_tool._last_ntp_time is None
    assert time_tool._last_web_time is None
    assert time_tool._time_offset == 0
    assert time_tool._web_session is None

