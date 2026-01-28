#!/usr/bin/env python
"""
Azure App Service entry point
This redirects to the Streamlit app
"""

import os
import sys

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

if __name__ == "__main__":
    os.system("streamlit run src/dashboard_interactive.py --server.port=8000 --server.address=0.0.0.0 --server.headless=true --server.enableCORS=false")
