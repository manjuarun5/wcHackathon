#!/bin/bash
set -e

echo "==================================="
echo "WCO Hackathon Dashboard - Starting"
echo "==================================="

# Get Python version
python --version

# Install dependencies
echo "Installing requirements..."
pip install --no-cache-dir -r requirements.txt

# Verify installation
echo "Verifying Streamlit installation..."
python -c "import streamlit; print(f'Streamlit version: {streamlit.__version__}')"

# Start the application
echo "Starting Streamlit app..."
exec streamlit run src/dashboard_interactive.py \
    --server.port=${PORT:-8000} \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --server.enableCORS=false \
    --server.enableXsrfProtection=false
