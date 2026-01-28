# WCO 2026 Hackathon - Customs E-Commerce Processing Pipeline

## Overview
This project is a customs e-commerce processing pipeline developed for the WCO 2026 Hackathon. It processes e-commerce orders, applies tariff classification, and provides an interactive dashboard for data visualization.

## Project Structure
```
sol-wco-hackathon/
├── docs/                    # Documentation files
├── input-data/             # Input data files
│   ├── ecommerce_orders.csv
│   └── tariff.csv
├── output-data/            # Processed output files
├── src/                    # Source code
│   ├── main.py            # Main processing script
│   └── dashboard.py       # Streamlit dashboard
└── requirements.txt       # Python dependencies
```

## Features
- E-commerce order processing
- Tariff classification
- Interactive dashboard with Streamlit
- Data visualization with Plotly

## Installation

1. Clone the repository:
```bash
git clone https://github.com/manjuarun5/wcHackathon.git
cd wcHackathon
```

2. Create and activate a virtual environment:
```bash
python -m venv .venv
# On Windows
.venv\Scripts\activate
# On macOS/Linux
source .venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Run the main processing script:
```bash
python src/main.py
```

### Launch the dashboard:
```bash
streamlit run src/dashboard.py
```

## Requirements
- Python 3.14+
- pandas >= 2.0.0
- numpy >= 1.24.0
- requests >= 2.31.0
- openai >= 1.12.0
- streamlit >= 1.28.0
- plotly >= 5.17.0

## License
This project was developed for the WCO 2026 Hackathon.

## Author
Manju Arun
