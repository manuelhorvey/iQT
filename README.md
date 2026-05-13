# Institutional Quant Trader

An institutional-grade quantitative trading pipeline supporting modular research, multi-asset risk management, ensemble signal generation, and production-ready live monitoring.

## Key Features

- **Multi-Asset Portfolio Engine**: Support for cross-sectional training and backtesting across Forex baskets (EURUSD, GBPUSD, USDJPY, etc.).
- **Institutional Risk Engine**: Professional position sizing using ATR-based lot calculation, variable spreads per asset, commission tracking, swap/rollover fees, and slippage modeling.
- **HMM Market Regime Detection**: Robust market state identification using scaled Gaussian Hidden Markov Models.
- **Ensemble Intelligence**: Multi-layer XGBoost ensemble trained on cross-sectional data with **SHAP-based explainability** for signal transparency.
- **Live Command Center**: Specialized execution desk dashboard providing real-time trade tickets, lot sizes, and portfolio risk oversight.

## Architecture

This project is built with a hybrid Python/C++ architecture:

1. **Python Quant Research Layer**:
   - `pandas`, `yfinance`, `pandas-ta`, `scikit-learn`, `hmmlearn`, `shap`
   - Handles data ingestion, regime detection, ensemble training, and live signal generation.

2. **C++ Execution Engine (Phase 5 - In Progress)**:
   - Built for low-latency market data ingestion and high-performance trade execution.
   - Connected via **ZeroMQ** for sub-millisecond signal handoff from the Python layer.

## Quick Start

### 1. Environment Setup

```bash
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Running Research Backtests
Generate a full portfolio backtest for Forex majors with institutional friction:
```bash
python src/python/main.py --mode backtest --tickers "EURUSD=X,GBPUSD=X,USDJPY=X,AUDUSD=X,USDCAD=X" --period 5y
```

### 3. Launching the Live Command Center
Generate actionable execution tickets for the current market state:
```bash
python src/python/main.py --mode live --threshold 65
```
*Reports are saved to `dashboard/live/live_command_center.html`.*

## Project Structure

```
institutional-quant-trader/
├── dashboard/         
│   ├── reports/       # Portfolio backtest research reports
│   └── live/          # Live execution tickets and command center
├── src/
│   ├── cpp/           # High-performance C++ execution/data engine
│   └── python/        
│       ├── main.py          # Unified pipeline entry point
│       ├── live_signals.py  # Execution ticket engine
│       ├── risk_manager.py  # Professional Forex risk module
│       ├── backtester.py    # Multi-asset institutional backtester
│       ├── ensemble.py      # XGBoost Ensemble + SHAP
│       └── regime.py        # HMM Regime Detection
└── README.md
```

## Institutional Metrics (Current FX Benchmark)
- **Sharpe Ratio**: 1.90
- **Max Drawdown**: -1.70%
- **Transaction Costs**: Variable Spreads + $5/lot Commission + Swaps + Slippage modeling included.

## Next Steps

- **ZeroMQ Bridge**: Finalize the publisher/subscriber layer for real-time Python -> C++ handoff.
- **Portfolio Walk-Forward Optimization**: Multi-fold validation to prevent data mining bias.
- **Live Broker API**: Integrate OANDA/IBKR for automated paper trading.
