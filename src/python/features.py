import pandas as pd
import pandas_ta as ta

class FeatureEngineer:
    def __init__(self, df):
        self.df = df.copy()

    def generate_features(self):
        print("Calculating technical indicators...")
        
        # Moving Averages
        self.df['SMA_20'] = ta.sma(self.df['Close'], length=20)
        self.df['SMA_50'] = ta.sma(self.df['Close'], length=50)
        self.df['SMA_200'] = ta.sma(self.df['Close'], length=200)
        
        # Momentum
        self.df['RSI_14'] = ta.rsi(self.df['Close'], length=14)
        macd = ta.macd(self.df['Close'], fast=12, slow=26, signal=9)
        self.df = pd.concat([self.df, macd], axis=1)
        
        # Volatility
        self.df['ATR_14'] = ta.atr(self.df['High'], self.df['Low'], self.df['Close'], length=14)
        
        # Returns
        self.df['Returns'] = self.df['Close'].pct_change()
        self.df['Log_Returns'] = ta.log_return(self.df['Close'])
        
        # Support and Resistance (simple rolling min/max)
        self.df['Support_20'] = self.df['Low'].rolling(window=20).min()
        self.df['Resistance_20'] = self.df['High'].rolling(window=20).max()
        
        # --- Institutional Feature Set (Alpha-Alpha) ---
        # 1. Rolling Z-Scores (Window: 20)
        # Normalizes indicators to be regime-agnostic
        for col in ['RSI_14', 'ATR_14']:
            self.df[f'{col}_Z'] = (self.df[col] - self.df[col].rolling(20).mean()) / self.df[col].rolling(20).std()
            
        # 2. Normalized SMA Distance
        self.df['SMA_Dist_Z'] = (self.df['Close'] - self.df['SMA_20']) / self.df['ATR_14']
        
        # 3. Multi-Period Lagged Returns
        for l in [1, 2, 3]:
            self.df[f'Ret_Lag_{l}'] = self.df['Returns'].shift(l)
            
        self.df.dropna(inplace=True)
        return self.df
