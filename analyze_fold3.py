#!/usr/bin/env python3
import sys
sys.path.insert(0, '/home/manuelhorveydaniel/Projects/institutional-quant-trader/src/intelligence')

from data_loader import DataManager
from features import FeatureEngineer
from regime import RegimeDetector
import pandas as pd
import numpy as np

# Load the same data as the WFO
tickers = ['EURUSD=X', 'GBPUSD=X', 'USDJPY=X', 'AUDUSD=X', 'USDCAD=X', 'GC=F']
manager = DataManager(tickers=tickers, provider_type='yfinance')
data_map = manager.get_data(period='5y')

# Process like the main pipeline
processed_data = {}
for ticker, df in data_map.items():
    engineer = FeatureEngineer(df)
    df = engineer.generate_features()
    detector = RegimeDetector()
    df = detector.fit_predict(df)
    processed_data[ticker] = df

# Get the master timeline (first ticker)
master_ticker = list(processed_data.keys())[0]
master_df = processed_data[master_ticker]
total_len = len(master_df)

print(f"Total data length: {total_len} days")
print(f"Date range: {master_df.index.min()} to {master_df.index.max()}\n")

# Replicate the WFO fold logic
n_folds = 5
for i in range(n_folds):
    mid_idx = int(total_len * (0.6 + 0.3 * (i / n_folds)))
    end_idx = int(mid_idx + (total_len * 0.08))
    if end_idx > total_len:
        end_idx = total_len
    
    is_start = master_df.index[0]
    is_end = master_df.index[mid_idx - 1]
    oos_start = master_df.index[mid_idx]
    oos_end = master_df.index[end_idx - 1]
    
    oos_len = end_idx - mid_idx
    
    print(f"Fold {i+1}:")
    print(f"  IS: {is_start.date()} to {is_end.date()} ({mid_idx} days)")
    print(f"  OOS: {oos_start.date()} to {oos_end.date()} ({oos_len} days)")
    
    # For fold 3, analyze volatility and trend
    if i == 2:  # Fold 3 (0-indexed)
        oos_df = master_df.iloc[mid_idx:end_idx]
        
        # Analyze the OOS period
        oos_returns = oos_df['Returns']
        oos_vol = oos_returns.std() * np.sqrt(252)
        oos_drift = oos_returns.mean() * 252
        
        print(f"\n  ** FOLD 3 ANALYSIS **")
        print(f"  Annualized Volatility: {oos_vol:.2%}")
        print(f"  Annualized Drift: {oos_drift:.2%}")
        print(f"  Skewness: {oos_returns.skew():.3f}")
        print(f"  Kurtosis: {oos_returns.kurtosis():.3f}")
        
        # Check regime distribution during fold 3
        if 'Regime_Label' in oos_df.columns:
            regime_counts = oos_df['Regime_Label'].value_counts()
            print(f"  Regime distribution (OOS):")
            for regime, count in regime_counts.items():
                print(f"    {regime}: {count} days ({count/len(oos_df):.1%})")
        
        # For context, show the surrounding folds too
        print(f"\n  Context (neighboring folds):")
        for j in [1, 2, 3]:
            if j != 2:
                mid_j = int(total_len * (0.6 + 0.3 * (j / n_folds)))
                end_j = int(mid_j + (total_len * 0.08))
                if end_j > total_len:
                    end_j = total_len
                fold_df = master_df.iloc[mid_j:end_j]
                fold_vol = fold_df['Returns'].std() * np.sqrt(252)
                fold_drift = fold_df['Returns'].mean() * 252
                print(f"    Fold {j+1} volatility: {fold_vol:.2%}, drift: {fold_drift:.2%}")
    
    print()
