import pytest
import pytest_asyncio
import asyncio
from app.agent.enhanced_radis import EnhancedRadis

@pytest_asyncio.fixture
async def agent():
    """
    Fixture that returns an instance of EnhancedRadis for use in tests.
    """
    agent = EnhancedRadis()
    yield agent
    # Clean up resources after test
    await agent.cleanup()
