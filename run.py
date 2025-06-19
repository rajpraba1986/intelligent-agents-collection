#!/usr/bin/env python3
"""
Entry point for the Agentic AI MCP application.
This script properly handles the Python path for imports.
"""

import sys
import os

# Add the src directory to the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(project_root, 'src')
sys.path.insert(0, src_path)

# Now import and run the main application
from main import main
import asyncio

if __name__ == "__main__":
    asyncio.run(main())
