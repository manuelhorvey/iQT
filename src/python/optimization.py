import pandas as pd
import numpy as np
from ensemble import EnsembleModel
from backtester import MultiAssetBacktester

class WalkForwardOptimizer:
    def __init__(self, data_map, n_folds=5, train_size=0.7, risk_manager=None):
        self.data_map = data_map
        self.n_folds = n_folds
        self.train_size = train_size
        self.risk_manager = risk_manager
        
    def run(self, feature_cols):
        print(f"Starting Multi-Asset Walk-Forward Optimization ({self.n_folds} folds)...")
        
        # We'll use the index of the first asset as the master timeline
        master_ticker = list(self.data_map.keys())[0]
        total_len = len(self.data_map[master_ticker])
        all_oos_returns = []
        fold_reports = []
        
        param_grid = [
            {'max_depth': 3, 'n_estimators': 100},
            {'max_depth': 5, 'n_estimators': 150},
        ]
        
        for i in range(self.n_folds):
            mid_idx = int(total_len * (0.6 + 0.3 * (i / self.n_folds)))
            end_idx = int(mid_idx + (total_len * 0.08))
            if end_idx > total_len: end_idx = total_len
            
            # Prepare Multi-Asset IS/OOS
            is_data_map = {t: df.iloc[:mid_idx] for t, df in self.data_map.items()}
            oos_data_map = {t: df.iloc[mid_idx:end_idx] for t, df in self.data_map.items()}
            
            if len(oos_data_map[master_ticker]) < 30: continue
            
            best_acc = 0
            best_model = None
            
            # 1. Multi-Asset Training (Pool all pairs)
            for params in param_grid:
                ensemble = EnsembleModel(params=params)
                X_is, y_is, _ = ensemble.prepare_multi_asset_data(is_data_map)
                ensemble.train(X_is, y_is)
                
                if ensemble.accuracy > best_acc:
                    best_acc = ensemble.accuracy
                    best_model = ensemble
            
            # 2. Multi-Asset Validation (True OOS)
            all_oos_X = []
            all_oos_y = []
            signaled_oos = {}
            for t, df in oos_data_map.items():
                # Prepare features/target for diagnostic
                X_o, y_o, _, f_cols = best_model.prepare_data(df)
                all_oos_X.append(X_o)
                all_oos_y.append(y_o)
                
                # Generate actual signals for backtesting (Dynamic Thresholding)
                signaled_oos[t] = best_model.generate_signals(df, f_cols, threshold=-1)
            
            X_oos_combined = pd.concat(all_oos_X)
            y_oos_combined = pd.concat(all_oos_y)
            
            from sklearn.metrics import accuracy_score
            oos_preds = best_model.model.predict(X_oos_combined)
            true_oos_acc = accuracy_score(y_oos_combined, oos_preds)
            
            print(f"Fold {i+1} Class Balance: {y_is.mean():.1%} Buy | OOS Acc: {true_oos_acc:.2%}")
            
            backtester = MultiAssetBacktester(signaled_oos, risk_manager=self.risk_manager)
            bt_res = backtester.run()
            metrics = backtester.calculate_metrics()
            
            fold_reports.append({
                'Fold': i + 1,
                'IS_Acc': f"{best_acc:.2%}",
                'OOS_Acc': f"{true_oos_acc:.2%}",
                'OOS_Sharpe': metrics['Sharpe Ratio'],
                'OOS_Return': metrics['Total Return']
            })
            
            all_oos_returns.append(bt_res['Strategy_Return'])
            
        return fold_reports, pd.concat(all_oos_returns)
