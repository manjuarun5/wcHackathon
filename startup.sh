#!/bin/bash

# Azure App Service startup script for Streamlit

echo "========================================="
echo "Starting WCO Hackathon Dashboard"
echo "========================================="

# Navigate to application directory
cd /home/site/wwwroot
echo "Current directory: $(pwd)"

# List files for debugging
echo "Files in wwwroot:"
ls -la

# Upgrade pip
echo "Upgrading pip..."
python -m pip install --upgrade pip

# Install dependencies
echo "Installing dependencies from requirements.txt..."
pip install -r requirements.txt --no-cache-dir

# Verify streamlit installation
echo "Streamlit version:"
streamlit --version

# Set Python path
export PYTHONPATH=/home/site/wwwroot:$PYTHONPATH

# Run Streamlit
echo "Starting Streamlit on port 8000..."
streamlit run src/dashboard_interactive.py \
    --server.port=8000 \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --server.enableCORS=false \
    --server.enableXsrfProtection=false \
    --browser.serverAddress="0.0.0.0" \
    --browser.gatherUsageStats=false
