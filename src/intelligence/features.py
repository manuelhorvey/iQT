import pandas as pd
import pandas_ta as ta

class FeatureEngineer:
    def __init__(self, df: pd.DataFrame) -> None:
        self.df = df.copy()

    def generate_features(self) -> pd.DataFrame:
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
        # 1. Rolling Z-Scores (Window: 60 - Increased for Regime Stability)
        # Normalizes indicators to be regime-agnostic
        for col in ['RSI_14', 'ATR_14']:
            self.df[f'{col}_Z'] = (self.df[col] - self.df[col].rolling(60).mean()) / self.df[col].rolling(60).std()
            
        # 2. Normalized SMA Distance (Window: 60)
        self.df['SMA_Dist_Z'] = (self.df['Close'] - self.df['SMA_20']) / self.df['ATR_14'].rolling(60).mean()
        
        # 3. Multi-Period Lagged Returns
        for l in [1, 2, 3]:
            self.df[f'Ret_Lag_{l}'] = self.df['Returns'].shift(l)
            
        # 4. Volatility Momentum (ATR Slope)
        self.df['ATR_Smooth'] = self.df['ATR_14'].rolling(window=5).mean()
        self.df['ATR_Slope'] = self.df['ATR_Smooth'].diff().fillna(0)
            
        self.df.dropna(inplace=True)
        return self.df
