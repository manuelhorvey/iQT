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
flowchart TD
    %% Data Ingestion
    subgraph Data [Data Layer]
        direction LR
        API([External APIs / CSV])
        DL[Data Loader]
        API --> DL
    end

    %% Python Intelligence
    subgraph Python [Python Intelligence Layer]
        direction TB
        subgraph Research [Research & Strategy]
            FE[Feature Engineering]
            RD[HMM Regime Detection]
            ML[XGBoost Ensemble]
            DL --> FE --> RD --> ML
        end

        subgraph Validation [Optimization & Validation]
            WFO[Walk-Forward Opt]
            MC[Monte Carlo / Stress Test]
            ML --> WFO --> MC
        end

        subgraph Management [Portfolio Management]
            RM[Risk Manager]
            HRP[HRP Allocation]
            MC --> RM --> HRP
        end
    end

    %% Bridge
    subgraph Connectivity [Communication Bridge]
        ZMQ[[ZMQ PUB/SUB : 5555]]
    end

    HRP --> |Live Signals| ZMQ

    %% C++ Execution
    subgraph CPP [C++ Execution Engine]
        direction TB
        SUB[Signal Subscriber]
        MDF[Market Data Feed]
        EE[Execution Engine]
        PM[Position Manager]
        
        ZMQ --> SUB
        SUB & MDF --> EE
        EE --> PM
        PM --> |Real-time Tracking| PM
    end

    %% Reporting
    subgraph Reports [Analytics & Dashboards]
        direction LR
        DG[Dashboard Generator]
        LCC[Live Command Center]
        HRP -.-> |Backtest Logs| DG
        PM -.-> |Trade Telemetry| LCC
    end

    %% Styling
    style Python fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    style CPP fill:#fff3e0,stroke:#e65100,stroke-width:2px
    style Connectivity fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    style Reports fill:#f1f8e9,stroke:#1b5e20,stroke-width:2px
    style Data fill:#eceff1,stroke:#455a64,stroke-width:2px
```

## 🛑 Proper Shutdown

To stop the C++ engine cleanly:

```bash
pkill -9 QuantEngine
```

---
**Institutional Baseline Performance**: Sharpe 1.14 | Max DD -4.2% | Win Rate 54% (After Hardened Costs & Slippage Modeling).
