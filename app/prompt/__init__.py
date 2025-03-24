"""
Prompt Module

This module contains prompt templates and constants used throughout the application.
"""

# Importing prompt constants from different modules
from app.prompt.planning import NEXT_STEP_PROMPT, SYSTEM_PROMPT
from app.prompt.swe import NEXT_STEP_TEMPLATE

# Exporting the prompts for easy access
__all__ = [
    "NEXT_STEP_PROMPT",
    "SYSTEM_PROMPT",
    "NEXT_STEP_TEMPLATE",
]

# Grouping related prompts together
PLANNING_PROMPTS = {
    "next_step": NEXT_STEP_PROMPT,
    "system": SYSTEM_PROMPT,
}

SWE_PROMPTS = {
    "next_step": NEXT_STEP_TEMPLATE,
}

# You can add more groups as needed for other prompt types
