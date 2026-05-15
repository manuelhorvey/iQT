import pandas as pd
import numpy as np
import pandas_ta as ta


class FeatureEngineer:
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()

    # ---------------------------------------------------
    # core feature pipeline
    # ---------------------------------------------------
    def generate_features(self) -> pd.DataFrame:
        df = self.df

        print("Calculating technical indicators...")

        # =========================
        # Core Returns (EV foundation) - Calculate FIRST
        # =========================
        df["Returns"] = df["Close"].pct_change()
        df["Log_Returns"] = np.log(df["Close"]).diff()

        # =========================
        # Trend
        # =========================
        df["SMA_20"] = ta.sma(df["Close"], length=20)
        df["SMA_50"] = ta.sma(df["Close"], length=50)
        df["SMA_200"] = ta.sma(df["Close"], length=200)

        # =========================
        # Momentum & Mean Reversion
        # =========================
        df["RSI_14"] = ta.rsi(df["Close"], length=14)
        df["RSI_7"] = ta.rsi(df["Close"], length=7) # Fast momentum
        
        # Bollinger Bands for Mean Reversion
        bbands = ta.bbands(df["Close"], length=20, std=2)
        if bbands is not None:
            # Use dynamic filtering to handle pandas_ta column naming variations
            bbu = bbands.filter(like="BBU").iloc[:, 0]
            bbl = bbands.filter(like="BBL").iloc[:, 0]
            
            df["BB_Width"] = (bbu - bbl) / df["Close"]
            df["BB_Pct"] = (df["Close"] - bbl) / (bbu - bbl + 1e-8)

        # =========================
        # Volatility & Noise
        # =========================
        df["ATR_14"] = ta.atr(df["High"], df["Low"], df["Close"], length=14)
        df["Vol_Ratio"] = df["ATR_14"] / df["ATR_14"].rolling(100).mean() # Volatility spikes
        df["Vol_of_Vol"] = df["Returns"].rolling(20).std().rolling(20).std()

        # Kaufman Efficiency Ratio (ER)
        change = (df["Close"] - df["Close"].shift(10)).abs()
        volatility = df["Returns"].abs().rolling(10).sum()
        df["Efficiency_Ratio"] = change / (volatility * df["Close"] + 1e-8)

        # =========================
        # Trend Context
        # =========================
        
        # Long-term context
        df["Dist_SMA_200"] = (df["Close"] - df["SMA_200"]) / (df["ATR_14"] * 10 + 1e-8)
        
        # Rolling skewness/kurtosis (Tail risk awareness)
        df["Skew_20"] = df["Returns"].rolling(20).skew()

        # =========================
        # Structure levels
        # =========================
        df["Support_20"] = df["Low"].rolling(20).min()
        df["Resistance_20"] = df["High"].rolling(20).max()

        # =========================
        # Robust Z-scores (stabilized)
        # =========================
        for col in ["RSI_14", "ATR_14"]:
            mean = df[col].rolling(60).mean()
            std = df[col].rolling(60).std()

            df[f"{col}_Z"] = (df[col] - mean) / (std + 1e-8)

        # =========================
        # Normalized SMA deviation
        # =========================
        atr_mean = df["ATR_14"].rolling(60).mean()

        df["SMA_Dist_Z"] = (df["Close"] - df["SMA_20"]) / (atr_mean + 1e-8)

        # =========================
        # Lagged returns
        # =========================
        for l in [1, 2, 3]:
            df[f"Ret_Lag_{l}"] = df["Returns"].shift(l)

        # =========================
        # Volatility dynamics
        # =========================
        df["ATR_Smooth"] = df["ATR_14"].rolling(5).mean()
        df["ATR_Slope"] = df["ATR_Smooth"].diff()

        # =========================
        # ADX (safe handling)
        # =========================
        adx = ta.adx(df["High"], df["Low"], df["Close"], length=14)

        if isinstance(adx, pd.DataFrame):
            df["ADX_14"] = adx.filter(like="ADX").iloc[:, 0]
        else:
            df["ADX_14"] = np.nan

        df["ADX_Trending"] = (df["ADX_14"] > 25).astype(int)

        # =========================
        # IMPORTANT FIX: volatility normalization
        # =========================
        df["ATR_Pct"] = df["ATR_14"] / (df["Close"] + 1e-8)

        # =========================
        # CLEANUP (EV SAFE)
        # =========================
        core_cols = ["Close", "High", "Low", "ATR_14", "Returns"]

        df = df.dropna(subset=core_cols)

        self.df = df
        return df

    # ---------------------------------------------------
    # macro injection (safe + non-recomputational)
    # ---------------------------------------------------
    def add_macro_features(self, dxy_slope: pd.Series = None) -> pd.DataFrame:
        if dxy_slope is not None:
            self.df["DXY_Slope_20"] = dxy_slope.reindex(self.df.index).ffill().fillna(0.0)
        else:
            self.df["DXY_Slope_20"] = 0.0

        return self.df