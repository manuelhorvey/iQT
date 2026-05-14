import numpy as np
import pandas as pd
from hmmlearn.hmm import GaussianHMM
from sklearn.preprocessing import StandardScaler
from typing import Dict

class RegimeDetector:
    def __init__(self, n_components: int = 2, random_state: int = 42) -> None:
        self.n_components = n_components
        self.random_state = random_state
        self.model = GaussianHMM(
            n_components=self.n_components, 
            covariance_type="full", 
            n_iter=2000, 
            random_state=self.random_state,
            init_params="mct"
        )
        self.scaler = StandardScaler()
        self.regime_map: Dict[int, str] = {}

    def fit_predict(self, df: pd.DataFrame) -> pd.DataFrame:
        print("Detecting market regimes using HMM (with scaling)...")
        # Ensure we don't have NaNs or infs
        data = df[['Returns', 'ATR_14']].dropna()
        
        # Scale features to mean 0, variance 1
        scaled_features = self.scaler.fit_transform(data)
        
        # Fit and predict
        self.model.fit(scaled_features)
        regimes = self.model.predict(scaled_features)
        
        # Map back to original dataframe (handling the dropped NaNs if any)
        df_out = df.copy()
        df_out['Regime'] = np.nan
        df_out.loc[data.index, 'Regime'] = regimes
        
        # Forward fill any NaNs at the beginning
        df_out['Regime'] = df_out['Regime'].ffill().bfill().astype(int)
        
        # Determine which regime is bullish vs bearish based on mean returns
        regime_means = df_out.groupby('Regime')['Returns'].mean()
        if regime_means.get(0, 0) > regime_means.get(1, 0):
            self.regime_map = {0: 'Bullish', 1: 'Bearish'}
        else:
            self.regime_map = {0: 'Bearish', 1: 'Bullish'}
            
        df_out['Regime_Label'] = df_out['Regime'].map(self.regime_map)
        return df_out
