from typing import Optional

from app.agent.base import BaseAgent
from app.agent.planning import PlanningAgent
from app.agent.react import ReActAgent
from app.agent.swe import SWEAgent
from app.agent.toolcall import ToolCallAgent
from app.agent.radis import Radis
from app.agent.enhanced_radis import EnhancedRadis

__all__ = [
    "BaseAgent",
    "PlanningAgent",
    "ReActAgent",
    "SWEAgent",
    "ToolCallAgent",
    "Radis",
    "EnhancedRadis",
]

# Additional Cross-Cutting Improvements

import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Example of logging usage in agent classes
def log_state_transition(agent_name: str, new_state: str):
    logger.info(f"{agent_name} transitioned to state: {new_state}")

def log_error(agent_name: str, error_message: str):
    logger.error(f"{agent_name} encountered an error: {error_message}")

# Example of standardizing error handling
def handle_error(e: Exception) -> str:
    """Convert an exception to a user-friendly message."""
    logger.error(f"An error occurred: {str(e)}")
    return "An unexpected error occurred. Please try again."

# Ensure all methods in agent classes have proper type annotations
# This will be done in the respective agent class files

# Implement test hooks in agent classes as needed
def add_test_hook(hook: Optional[callable] = None):
    """Add a test hook for external dependencies."""
    if hook:
        logger.info("Test hook added.")
