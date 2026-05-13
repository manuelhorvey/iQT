import pandas as pd
import numpy as np
from ensemble import EnsembleModel
from backtester import MultiAssetBacktester

class WalkForwardOptimizer:
    def __init__(self, df, n_folds=5, train_size=0.7, risk_manager=None):
        self.df = df.copy()
        self.n_folds = n_folds
        self.train_size = train_size
        self.risk_manager = risk_manager
        
    def run(self, feature_cols):
        print(f"Starting Walk-Forward Optimization ({self.n_folds} folds)...")
        
        # Calculate size of each fold
        total_len = len(self.df)
        fold_size = total_len // self.n_folds
        
        all_oos_returns = []
        fold_results = []
        
        for i in range(self.n_folds):
            # Define IS and OOS boundaries
            # Expanding window approach or rolling window? Let's use rolling for robustness.
            start_idx = i * (total_len // (self.n_folds + 1))
            mid_idx = int(start_idx + (total_len // (self.n_folds + 1)) * self.train_size)
            end_idx = start_idx + (total_len // (self.n_folds + 1))
            
            is_df = self.df.iloc[start_idx:mid_idx]
            oos_df = self.df.iloc[mid_idx:end_idx]
            
            if len(oos_df) < 20: continue # Skip tiny folds
            
            print(f"Fold {i+1}: Training {is_df.index[0].date()} to {is_df.index[-1].date()} | Testing {oos_df.index[0].date()} to {oos_df.index[-1].date()}")
            
            # Train model on IS
            ensemble = EnsembleModel()
            X_is, y_is, _, _ = ensemble.prepare_data(is_df)
            ensemble.train(X_is, y_is)
            
            # Generate signals on OOS
            oos_df_signals = ensemble.generate_signals(oos_df, feature_cols)
            
            # Backtest OOS (Wrap single DF in dict for MultiAssetBacktester)
            backtester = MultiAssetBacktester({"asset": oos_df_signals}, risk_manager=self.risk_manager)
            bt_res = backtester.run()
            metrics = backtester.calculate_metrics()
            
            fold_results.append({
                'Fold': i + 1,
                'Start': oos_df.index[0].date(),
                'End': oos_df.index[-1].date(),
                'OOS_Return': metrics['Total Return'],
                'OOS_Sharpe': metrics['Sharpe Ratio']
            })
            
            all_oos_returns.append(bt_res['Strategy_Return'])
            
        # Aggregate OOS Results
        oos_returns_series = pd.concat(all_oos_returns)
        
        # Calculate Robustness Score (Aggregate OOS Sharpe / IS Average Sharpe)
        # For simplicity, let's just return fold metrics for now
        return fold_results, oos_returns_series
