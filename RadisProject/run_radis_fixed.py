#!/usr/bin/env python3
"""
Run RadisAgent with fixes for NoneType errors
"""

import os
import sys
import traceback
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("run_radis_fixed")

def main():
    """Main entry point"""
    # Add current directory to path
    sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
    
    # Apply LMStudio patch
    try:
        import lmstudio_patch
        logger.info("LMStudio patch applied")
    except ImportError:
        logger.warning("LMStudio patch not found")
    
    # Apply RadisAgent NoneType fix
    try:
        import fix_radis_nonetype
        logger.info("RadisAgent NoneType fix applied")
    except ImportError:
        logger.warning("RadisAgent NoneType fix not found")
        
    # Determine which script to run based on arguments
    if len(sys.argv) >= 2 and not sys.argv[1].startswith('-'):
        # If there's a positional argument, assume it's a query for run.sh
        import subprocess
        cmd = ['./run.sh'] + sys.argv[1:]
        logger.info(f"Running command: {' '.join(cmd)}")
        subprocess.call(cmd)
    else:
        # Otherwise, run run_flow.py
        import runpy
        logger.info("Running run_flow.py...")
        runpy.run_module('run_flow', run_name='__main__')

if __name__ == "__main__":
    main()
