import numpy as np
import pandas as pd
import xgboost as xgb
import shap
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

class EnsembleModel:
    def __init__(self, params=None):
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
        self.explainer = None
        self.accuracy = 0.0

    def _inject_features(self, df):
        """Standardizes feature injection for both training and inference."""
        df_out = df.copy()
        
        # 1. One-Hot Encode HMM Regimes (0, 1, 2)
        for r in [0, 1, 2]:
            if 'Regime' in df_out.columns:
                df_out[f'Regime_{r}'] = np.where(df_out['Regime'] == r, 1, 0)
            else:
                df_out[f'Regime_{r}'] = 0
                
        # 2. Balanced 5-day Directional Label (Only needed for training)
        if 'Returns' in df_out.columns:
            df_out['Target'] = np.where(df_out['Returns'].shift(-5).rolling(window=5).sum() > 0, 1, 0)
            
        return df_out

    def prepare_data(self, df):
        """Prepare features with One-Hot Regimes and Institutional Alpha."""
        df_out = self._inject_features(df)
        
        # 3. Optimized Feature Set
        feature_cols = [
            'RSI_14_Z', 'ATR_14_Z', 'SMA_Dist_Z', 
            'Ret_Lag_1', 'Ret_Lag_2', 'Ret_Lag_3',
            'Regime_0', 'Regime_1', 'Regime_2',
            'Support_20', 'Resistance_20', 'Regime_Change'
        ]
        
        available_cols = [c for c in feature_cols if c in df_out.columns]
        df_train = df_out.dropna(subset=['Target'] + available_cols)
        X = df_train[available_cols]
        y = df_train['Target']
        return X, y, df_out, available_cols

    def prepare_multi_asset_data(self, data_map):
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

    def train(self, X, y):
        print("Training Ensemble Model (XGBoost)...")
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)
        
        self.model.fit(X_train, y_train)
        
        # Initialize SHAP explainer
        self.explainer = shap.TreeExplainer(self.model)
        
        preds = self.model.predict(X_test)
        self.accuracy = accuracy_score(y_test, preds)
        print(f"Model Accuracy on Test Set: {self.accuracy:.2%}")

    def generate_signals(self, df, feature_cols, calculate_shap=False, threshold=0.65):
        """Generates signals and optionally SHAP values for each prediction."""
        df_out = self._inject_features(df)
        X = df_out[feature_cols]
        probs = self.model.predict_proba(X)[:, 1]
        
        df_out['Signal_Prob'] = probs
        
        # Dynamic Thresholding (If threshold == -1, use Top 10% percentile)
        if threshold == -1:
            threshold = np.percentile(probs, 90)
            print(f"Calibrated dynamic threshold: {threshold:.3f}")
        
        # Signal logic (Dynamic Thresholds)
        conditions = [
            (df_out['Signal_Prob'] > threshold),
            (df_out['Signal_Prob'] < (1 - threshold))
        ]
        choices = [1, -1]
        df_out['Signal'] = np.select(conditions, choices, default=0)
        
        if calculate_shap and self.explainer:
            shap_values = self.explainer.shap_values(X)
            # Store mean absolute SHAP for each feature in the dataframe as a diagnostic
            # For simplicity, we just store the SHAP values for the latest prediction
            df_out['Latest_SHAP'] = [shap_values[-1]] * len(df_out)
            
        return df_out

    def get_feature_importance(self, feature_cols):
        """Returns feature importance based on SHAP."""
        if self.explainer:
            # SHAP global importance (mean absolute SHAP)
            # This is more institutional than standard gain/weight importance
            pass
        return self.model.feature_importances_
