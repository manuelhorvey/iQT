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
USDSGD=X,USDHKD=X,USDMXN=X,USDZAR=X,USDTRY=X"

# 2. Setup Environment
source venv/bin/activate

# 3. Launch the Monitor
echo "=============================================================================="
echo " LAUNCHING FULL PORTFOLIO MONITOR (34 ASSETS) "
echo "=============================================================================="
python src/python/main.py --mode live --threshold 55 --tickers "$TICKERS"

echo "=============================================================================="
echo " Monitor Session Complete. Check dashboard/live/ for telemetry. "
echo "=============================================================================="
