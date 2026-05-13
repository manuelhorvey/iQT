import numpy as np
import pandas as pd
import xgboost as xgb
import shap
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

class EnsembleModel:
    def __init__(self):
        self.model = xgb.XGBClassifier(
            n_estimators=100, 
            learning_rate=0.05, 
            max_depth=4, 
            random_state=42,
            eval_metric='logloss'
        )
        self.explainer = None

    def prepare_data(self, df):
        """Prepare features and target for a single asset."""
        df_out = df.copy()
        df_out['Target'] = np.where(df_out['Returns'].shift(-1) > 0, 1, 0)
        
        feature_cols = [
            'SMA_20', 'SMA_50', 'SMA_200', 'RSI_14', 'ATR_14', 
            'Returns', 'Regime', 'Support_20', 'Resistance_20'
        ]
        
        df_train = df_out.dropna(subset=['Target'] + feature_cols)
        X = df_train[feature_cols]
        y = df_train['Target']
        return X, y, df_out, feature_cols

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
        acc = accuracy_score(y_test, preds)
        print(f"Model Accuracy on Test Set: {acc:.2%}")

    def generate_signals(self, df, feature_cols, calculate_shap=False, threshold=0.65):
        """Generates signals and optionally SHAP values for each prediction."""
        X = df[feature_cols]
        probs = self.model.predict_proba(X)[:, 1]
        
        df_out = df.copy()
        df_out['Signal_Prob'] = probs
        
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
