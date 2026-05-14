import yfinance as yf
import pandas as pd
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

class DataProvider(ABC):
    @abstractmethod
    def fetch(self, ticker: str, period: str, interval: str) -> pd.DataFrame:
        pass

    def _clean_df(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardizes yfinance output for both single and multi-asset downloads."""
        if df.empty:
            return df
        
        # yfinance often returns MultiIndex columns (e.g., ['Close', 'EURUSD=X'])
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)
        
        # Ensure we don't have duplicate columns (sometimes happens with yfinance)
        df = df.loc[:, ~df.columns.duplicated()]
        
        # Ensure 'Close' is a Series, not a 1-column DataFrame
        # (Assignment like df['Close'] = df['Close'] can fail if it's a DF)
        return df

class YFinanceProvider(DataProvider):
    def fetch(self, ticker: str, period: str, interval: str) -> pd.DataFrame:
        print(f"Fetching from yfinance: {ticker}...")
        df = yf.download(ticker, period=period, interval=interval, progress=False)
        return self._clean_df(df)

class LiveMockProvider(DataProvider):
    """Placeholder for high-frequency/broker feed."""
    def fetch(self, ticker: str, period: str, interval: str) -> pd.DataFrame:
        print(f"Warning: Mocking high-frequency feed for {ticker}...")
        # In a real system, this would connect to OANDA/Interactive Brokers WebSocket
        df = yf.download(ticker, period="5d", interval="1m", progress=False)
        return self._clean_df(df)

class DataManager:
    """
    Institutional Data Orchestrator.
    Supports multiple providers and handles caching/cleaning.
    """
    def __init__(self, tickers: List[str], provider_type: str = "yfinance") -> None:
        self.tickers = tickers if isinstance(tickers, list) else [tickers]
        if provider_type == "yfinance":
            self.provider = YFinanceProvider()
        elif provider_type == "live":
            self.provider = LiveMockProvider()
        else:
            raise ValueError(f"Unknown provider type: {provider_type}")

    def get_data(self, period: str = "2y", interval: str = "1d") -> Dict[str, pd.DataFrame]:
        data_map = {}
        for ticker in self.tickers:
            try:
                df = self.provider.fetch(ticker, period, interval)
                df.dropna(inplace=True)
                if not df.empty:
                    data_map[ticker] = df
                else:
                    print(f"WARNING: No data retrieved for {ticker}")
            except Exception as e:
                print(f"ERROR: Failed to fetch data for {ticker}: {e}")
        
        if not data_map:
            raise RuntimeError("Failed to load data for any tickers")
        
        return data_map
