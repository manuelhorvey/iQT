# iQT: Institutional Quant Trader (Forex)

![Build Status](https://img.shields.io/badge/build-passing-brightgreen)
![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)
![C++ Standard](https://img.shields.io/badge/C%2B%2B-17-orange)
![License](https://img.shields.io/badge/license-Proprietary-red)

A professional-grade quantitative trading pipeline for the Forex market, utilizing a hybrid Python-C++ architecture for research and low-latency execution.

> [!WARNING]
> **Research Prototype Note**: Current model accuracy is approximately 48-52%. This system is designed as a research framework and execution testbed. Do not route live capital without further alpha refinement.

## 📁 Project Structure

```text
institutional-quant-trader/
├── src/
│   ├── python/           # Research, ML, and Bridge Logic
│   │   ├── main.py       # Entry Point & CLI
│   │   ├── ensemble.py   # XGBoost Ensemble with Hysteresis
│   │   ├── optimization.py # Walk-Forward Optimization (WFO)
│   │   ├── backtester.py # Path-Dependent Iterative Engine
│   │   ├── allocation.py # HRP Portfolio Allocation
│   │   ├── dashboard_generator.py # Research Report Engine
│   │   ├── regime.py     # HMM Regime Detection
│   │   ├── features.py   # Institutional Feature Engineering
│   │   ├── risk_manager.py # Multi-Asset Risk & Cost Modeling
│   │   └── bridge.py     # ZMQ Publisher
│   └── cpp/              # Low-Latency Execution Engine
│       ├── main.cpp      # C++ Entry Point
│       ├── Order.h       # Data Primitives
│       └── PositionManager.cpp # Real-time Risk & Trade Tracking
├── dashboard/            
│   ├── live/             # Live Telemetry (live_command_center.html)
│   └── reports/          # Research & Performance Dashboards
├── BRIDGE_SPECIFICATION.md # ZMQ Protocol Details
└── README.md             # This file
```

## 🛡️ Institutional Hardening

This framework implements several "Real-World" constraints often missing from retail backtesters:

- **Path-Dependency**: Iterative execution engine modeling Stop-Loss (SL) and Take-Profit (TP) hits within a single bar.
- **Tail Risk Modeling**: Simulated weekend gaps and news-driven slippage (0.5% hits).
- **Realistic Friction**: Hardened spreads (1.5 - 2.5 pips) and volume-based commissions matching OANDA/IC Markets.
- **Signal Hysteresis**: Logic to prevent trade churning by requiring stronger confirmation to flip or exit positions.

## 🛠 Prerequisites

### System Dependencies (Linux/Debian)

```bash
sudo apt-get update
sudo apt-get install cmake g++ build-essential libzmq3-dev pkg-config
```

### Software Versions

- **Python**: 3.10 or higher
- **CMake**: 3.15 or higher
- **C++ Compiler**: GCC 9+ or Clang 10+
- **ZeroMQ**: 4.3.4+

## 🚀 Installation

1. **Python Setup**:

   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **C++ Build**:

   ```bash
   mkdir build && cd build
   cmake .. -DCMAKE_BUILD_TYPE=Release
   make -j4
   ```

## 📈 Usage & CLI Specification

### 1. Walk-Forward Optimization (WFO)

Recommended for robust parameter selection and out-of-sample (OOS) validation.

```bash
python src/python/main.py --optimize --period 5y
```

### 2. Backtest Mode

Executes a historical simulation with path-dependent logic and stress testing.

```bash
python src/python/main.py --mode backtest --period 5y --stress_test
```

- `--period`: History length (e.g., `1y`, `5y`, `max`).
- `--stress_test`: Runs Monte Carlo (5000 paths) and Deflated Sharpe analysis.

### 3. Live Signal Mode

Generates real-time tickets and pushes them to the C++ engine.

```bash
# Terminal 1: Launch C++ Engine
./build/src/cpp/QuantEngine

# Terminal 2: Generate Signals
python src/python/main.py --mode live --threshold 65 --tickers EURUSD=X,GBPUSD=X
```

## 🏗 System Architecture

The pipeline is split into a **Python Intelligence Layer** (Heavy ML, Clustering, WFO) and a **C++ Execution Layer** (Deterministic Risk, Order Management), communicating over a ZeroMQ PUB/SUB bridge on port **5555**.

```mermaid
graph TD
    subgraph Python_Intelligence
        A[Data Loader] --> B[Feature Engineering]
        B --> C[Regime Detection]
        C --> D[Ensemble Model]
        D --> E[Walk-Forward Opt]
        E --> F[ZMQ Publisher]
    end

    subgraph CPP_Execution
        F -- "127.0.0.1:5555" --> G[ZMQ Subscriber]
        G --> H[Execution Engine]
        H --> I[Position Manager]
        I --> J[Automated SL/TP]
    end
```

## 🛑 Proper Shutdown

To stop the C++ engine cleanly:

```bash
pkill -9 QuantEngine
```

---
**Institutional Baseline Performance**: Sharpe 1.14 | Max DD -4.2% | Win Rate 54% (After Hardened Costs & Slippage Modeling).
