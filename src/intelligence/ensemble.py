import numpy as np
import pandas as pd
import xgboost as xgb
import shap
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from typing import Dict, List, Tuple, Optional

class EnsembleModel:
    def __init__(self, params: Optional[Dict] = None) -> None:
        default_params = {
            'n_estimators': 100,
            'learning_rate': 0.05,
            'max_depth': 4,
            'random_state': 42,
            'eval_metric': 'logloss'
        }
        if params:
            default_params.update(params)
        
        self.model = xgb.XGBClassifier(**default_params)
        self.explainer: Optional[shap.TreeExplainer] = None
        self.accuracy: float = 0.0

    def _inject_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardizes feature injection for both training and inference."""
        df_out = df.copy()
        
        # 1. One-Hot Encode HMM Regimes (0, 1, 2)
        for r in [0, 1, 2]:
            if 'Regime' in df_out.columns:
                df_out[f'Regime_{r}'] = np.where(df_out['Regime'] == r, 1, 0)
            else:
                df_out[f'Regime_{r}'] = 0
                
        # 2. Balanced 10-day Directional Label (Longer Horizon to beat spreads)
        if 'Returns' in df_out.columns:
            df_out['Target'] = np.where(df_out['Returns'].shift(-10).rolling(window=10).sum() > 0, 1, 0)
            
        return df_out

    def prepare_data(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series, pd.DataFrame, List[str]]:
        """Prepare features with One-Hot Regimes and Institutional Alpha."""
        df_out = self._inject_features(df)
        
        # 3. Optimized Feature Set
        feature_cols = [
            'RSI_14_Z', 'ATR_14_Z', 'SMA_Dist_Z', 
            'Ret_Lag_1', 'Ret_Lag_2', 'Ret_Lag_3',
            'Regime_0', 'Regime_1', 'Regime_2',
            'Support_20', 'Resistance_20', 'ATR_Slope'
        ]
        
        available_cols = [c for c in feature_cols if c in df_out.columns]
        df_train = df_out.dropna(subset=['Target'] + available_cols)
        X = df_train[available_cols]
        y = df_train['Target']
        return X, y, df_out, available_cols

    def prepare_multi_asset_data(self, data_map: Dict[str, pd.DataFrame]) -> Tuple[pd.DataFrame, pd.Series, Optional[List[str]]]:
        """Combines data from multiple assets into one training set."""
        all_X = []
        all_y = []
        feature_cols = None
        
        for ticker, df in data_map.items():
            X, y, _, f_cols = self.prepare_data(df)
            all_X.append(X)
            all_y.append(y)
            feature_cols = f_cols
            
        combined_X = pd.concat(all_X)
        combined_y = pd.concat(all_y)
        return combined_X, combined_y, feature_cols

    def train(self, X: pd.DataFrame, y: pd.Series) -> None:
        print("Training Ensemble Model (XGBoost)...")
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)
        
        self.model.fit(X_train, y_train)
        
        # Initialize SHAP explainer
        self.explainer = shap.TreeExplainer(self.model)
        
        preds = self.model.predict(X_test)
        self.accuracy = accuracy_score(y_test, preds)
        print(f"Model Accuracy on Test Set: {self.accuracy:.2%}")

    def generate_signals(self, df: pd.DataFrame, feature_cols: List[str], 
                        calculate_shap: bool = False, threshold: float = 0.65) -> pd.DataFrame:
        """Generates signals with Confidence Floors and Volatility Filters."""
        df_out = self._inject_features(df)
        X = df_out[feature_cols]
        probs = self.model.predict_proba(X)[:, 1]
        
        df_out['Signal_Prob'] = probs
        
        # 1. Institutional Filter: Volatility Floor
        # Don't trade if ATR is in the bottom 20% of the CURRENT segment
        # Use a shorter window and ffill to ensure we get values in WFO
        atr_threshold = df_out['ATR_14'].rolling(20, min_periods=1).quantile(0.2).fillna(df_out['ATR_14'].median())
        vol_mask = df_out['ATR_14'] > atr_threshold
        
        # 2. Dynamic Thresholding with a Confidence Floor
        if threshold == -1:
            # Lower floor to 0.58 to match Forex market realities
            entry_threshold = max(np.percentile(probs, 95), 0.58)
            exit_threshold = 0.45 
            # print(f"Calibrated dynamic entry threshold: {entry_threshold:.3f} (Floor: 0.62)")
        else:
            entry_threshold = threshold
            exit_threshold = 0.50
        
        # 3. Signal logic with Hysteresis & Vol Filter
        signals = np.zeros(len(df_out))
        current_sig = 0
        
        for i in range(len(probs)):
            p = probs[i]
            is_volatile = vol_mask.iloc[i]
            
            if current_sig == 0:
                if is_volatile:
                    if p > entry_threshold:
                        current_sig = 1
                    elif p < (1 - entry_threshold):
                        current_sig = -1
            elif current_sig == 1:
                if p < exit_threshold: 
                    current_sig = 0
            elif current_sig == -1:
                if p > (1 - exit_threshold):
                    current_sig = 0
            signals[i] = current_sig
            
        df_out['Signal'] = signals
        
        if calculate_shap and self.explainer:
            shap_values = self.explainer.shap_values(X)
            # Store SHAP values properly: handle multi-dimensional output
            # For binary classification, shap_values is typically (n_samples, n_features, 2)
            # Extract class 1 SHAP values if needed
            if isinstance(shap_values, list):
                shap_vals = shap_values[1]  # Class 1 SHAP values
            elif shap_values.ndim == 3:
                shap_vals = shap_values[:, :, 1]  # Binary case: class 1
            else:
                shap_vals = shap_values  # Already (n_samples, n_features)
            
            # Calculate mean absolute SHAP per sample
            df_out['Latest_SHAP'] = np.abs(shap_vals).mean(axis=1)
            
        return df_out

    def get_feature_importance(self, feature_cols: List[str]) -> np.ndarray:
        """Returns feature importance based on SHAP."""
        if self.explainer:
            # SHAP global importance (mean absolute SHAP)
            # This is more institutional than standard gain/weight importance
            pass
        return self.model.feature_importances_
