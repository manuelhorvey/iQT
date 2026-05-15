#!/bin/bash

# ==============================================================================
# Institutional Quant Trader: Full Portfolio Monitor
# Monitors 34+ assets with HRP Allocation and Hardened Bridge.
# ==============================================================================

# 1. Define the full institutional basket (34 pairs)
TICKERS="EURUSD=X,GBPUSD=X,USDJPY=X,AUDUSD=X,USDCAD=X,NZDUSD=X,USDCHF=X,\
EURGBP=X,EURJPY=X,GBPJPY=X,AUDJPY=X,CHFJPY=X,EURCHF=X,EURAUD=X,\
GBPAUD=X,AUDCAD=X,NZDJPY=X,EURCAD=X,GBPCAD=X,AUDNZD=X,CADJPY=X,\
EURNZD=X,GBPNZD=X,GBPCHF=X,CADCHF=X,NZDCAD=X,NZDCHF=X,AUDCHF=X,\
GC=F"

set -euo pipefail

# 2. Setup Environment
source venv/bin/activate

ENGINE_BIN="./build/src/cpp/QuantEngine"
ENGINE_LOG="logs/quantengine.log"

cleanup() {
    if [ -n "${ENGINE_PID-}" ] && kill -0 "$ENGINE_PID" >/dev/null 2>&1; then
        echo "Shutting down QuantEngine (PID=$ENGINE_PID)..."
        kill "$ENGINE_PID" >/dev/null 2>&1 || true
        wait "$ENGINE_PID" 2>/dev/null || true
    fi
}
trap cleanup EXIT INT TERM

if [ ! -x "$ENGINE_BIN" ]; then
    echo "Error: C++ engine binary not found at $ENGINE_BIN"
    echo "Please build the project first (e.g. cmake --build build --target QuantEngine)."
    exit 1
fi

mkdir -p "$(dirname "$ENGINE_LOG")"

echo "=============================================================================="
echo " STARTING C++ EXECUTION ENGINE "
echo "=============================================================================="
"$ENGINE_BIN" > "$ENGINE_LOG" 2>&1 &
ENGINE_PID=$!

# Wait for the C++ engine to initialize
echo "Waiting for C++ engine to initialize..."
for i in $(seq 1 20); do
    if grep -q "Engine ready" "$ENGINE_LOG" 2>/dev/null; then
        echo "C++ Engine Ready."
        break
    fi
    if ! kill -0 "$ENGINE_PID" 2>/dev/null; then
        echo "Error: C++ Engine died during startup."
        cat "$ENGINE_LOG"
        exit 1
    fi
    sleep 0.5
done

# 3. Launch the Monitor
echo "=============================================================================="
echo " LAUNCHING FULL PORTFOLIO MONITOR (34 ASSETS) "
echo "=============================================================================="
python src/intelligence/main.py --mode live --threshold 55 --regime_gating 0.6 --tickers "$TICKERS"

echo "=============================================================================="
echo " Monitor Session Complete. Check dashboard/live/ for telemetry. "
echo "=============================================================================="
