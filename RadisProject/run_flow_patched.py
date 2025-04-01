#!/usr/bin/env python3
"""
Patched run_flow.py to fix NoneType error
"""

import os
import sys
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("run_flow_patched")

# Add current directory to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Apply patches first
logger.info("Applying patches...")

# Apply LMStudio patch
try:
    import lmstudio_patch
    logger.info("LMStudio patch applied")
except ImportError:
    logger.warning("LMStudio patch not found")

# Apply run_flow patch
try:
    import run_flow_patch
    logger.info("Run Flow patch applied")
except ImportError:
    logger.warning("Run Flow patch not found")

# Now import and run the original module
import runpy
logger.info("Running run_flow.py...")
runpy.run_module('run_flow', run_name='__main__')
