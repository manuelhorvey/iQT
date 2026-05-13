# Institutional Quant Trader

An institutional-grade quantitative trading pipeline supporting modular research, robust signal generation, backtesting, and production execution.

## Architecture

This project is built with a hybrid Python/C++ architecture:

1. **Python Quant Research Layer**:
   - `pandas`, `yfinance`, `pandas-ta`, `scikit-learn`, `hmmlearn`
   - Handles rapid prototyping, regime detection, technical indicator calculations, and interactive report generation.

2. **C++ Execution Engine (Phase 4)**:
   - Built for low-latency market data ingestion and high-frequency trade execution.
   - Core files available in `src/cpp/` (CMake setup included).

## Project Structure

```
institutional-quant-trader/
├── backtests/         # Historical backtesting scripts and configurations
├── config/            # System configuration (JSON/YAML)
├── dashboard/         # UI elements, generated HTML reports, and dash apps
│   └── reports/       # Output directory for HTML quant reports
├── data/              # Market data storage
│   ├── external/      # Third-party data (e.g. macro factors)
│   ├── processed/     # Cleaned and normalized tick/OHLCV data
│   └── raw/           # Raw uncompressed data dumps
├── models/            # Serialized ML models (HMM, XGBoost, etc.)
├── research/
│   └── notebooks/     # Jupyter Notebooks for exploratory data analysis
├── signals/           # Signal generation logic (Ensemble, SR, etc.)
├── src/
│   ├── cpp/           # High-performance C++ execution/data engine
│   └── python/        # Python quant analysis pipeline
└── tests/             # Unit and integration tests
```

## Quick Start

### Python Setup

1. Create a Python virtual environment and activate it:
   ```bash
   python3.12 -m venv venv
   source venv/bin/activate
   ```

2. Install the requirements:
   ```bash
   pip install -r requirements.txt
   ```

### Running the MVP Quant Report Generator

You can generate a comprehensive quant analysis report (including moving averages, RSI, ATR, and HMM regime detection) for any stock ticker:

```bash
source venv/bin/activate
python src/python/report_generator.py --ticker AAPL
```

The resulting HTML report will be saved to `dashboard/reports/AAPL_report.html`.

### C++ Engine Setup

To build the C++ execution engine skeleton:

```bash
mkdir -p src/cpp/build
cd src/cpp/build
cmake ../..
make
```

## Next Steps

- Expand technical signals module into discrete classes.
- Construct the ensemble model layer combining multiple models into trade probabilities.
- Introduce vectorized backtesting frameworks for validating signals over large historic datasets.
- Start implementing real-time market data ingestion via the C++ engine.
