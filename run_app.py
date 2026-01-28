#!/usr/bin/env python
"""
Run script for Azure deployment
Ensures dependencies are installed before starting Streamlit
"""

import subprocess
import sys
import os

def install_dependencies():
    """Install requirements"""
    print("Installing dependencies...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    print("Dependencies installed successfully!")

def run_streamlit():
    """Run the Streamlit app"""
    port = os.environ.get("PORT", "8000")
    print(f"Starting Streamlit on port {port}...")
    
    subprocess.run([
        sys.executable, "-m", "streamlit", "run",
        "src/dashboard_interactive.py",
        f"--server.port={port}",
        "--server.address=0.0.0.0",
        "--server.headless=true",
        "--server.enableCORS=false",
        "--server.enableXsrfProtection=false"
    ])

if __name__ == "__main__":
    install_dependencies()
    run_streamlit()
