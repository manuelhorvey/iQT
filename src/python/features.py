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
        
        self.df.dropna(inplace=True)
        return self.df
