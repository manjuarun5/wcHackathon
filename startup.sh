#!/bin/bash

# Azure App Service startup script for Streamlit

echo "Starting Streamlit application..."

# Navigate to application directory
cd /home/site/wwwroot

# Install dependencies if not already installed
pip install -r requirements.txt

# Run Streamlit
streamlit run src/dashboard_interactive.py \
    --server.port=8000 \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --server.enableCORS=false \
    --server.enableXsrfProtection=false
