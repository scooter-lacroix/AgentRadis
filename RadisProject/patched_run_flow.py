#!/usr/bin/env python3

# Import patch first
import lmstudio_patch

# Run the original run_flow.py
import sys
import runpy
runpy.run_module('run_flow', run_name='__main__')
