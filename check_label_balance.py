#!/usr/bin/env python3
import sys
sys.path.insert(0, '/home/manuelhorveydaniel/Projects/institutional-quant-trader/src/intelligence')

from data_loader import DataManager
from features import FeatureEngineer
from regime import RegimeDetector
from ensemble import EnsembleModel
import pandas as pd

tickers = ['EURUSD=X', 'GBPUSD=X']
manager = DataManager(tickers=tickers, provider_type='yfinance')
data_map = manager.get_data(period='5y')

processed_data = {}
for ticker, df in data_map.items():
    engineer = FeatureEngineer(df)
    df = engineer.generate_features()
    detector = RegimeDetector()
    df = detector.fit_predict(df)
    processed_data[ticker] = df

ensemble = EnsembleModel()
X, y, _ = ensemble.prepare_multi_asset_data(processed_data)

print(f"Total labels: {len(y)}")
print(f"Class 0 (Down): {(y == 0).sum()} ({(y == 0).mean():.1%})")
print(f"Class 1 (Up): {(y == 1).sum()} ({(y == 1).mean():.1%})")
print(f"\nTarget definition: Returns.shift(-1) > 1.5 * ATR_14")
