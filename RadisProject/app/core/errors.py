"""This module is deprecated. Import error classes from app.errors instead."""

import warnings
from app.errors import (
    RadisError,
    ToolError,
    PlanningError,
    ConfigurationError,
    DisplayError,
)

warnings.warn(
    "Importing from app.core.errors is deprecated. "
    "Please import directly from app.errors instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "RadisError",
    "ToolError",
    "PlanningError",
    "ConfigurationError",
    "DisplayError",
]
