import yfinance as yf
import pandas as pd

class DataLoader:
    def __init__(self, tickers, period="2y", interval="1d"):
        self.tickers = tickers if isinstance(tickers, list) else [tickers]
        self.period = period
        self.interval = interval

    def fetch_data(self):
        """
        Fetches data for all tickers and returns a dictionary of DataFrames.
        """
        data_map = {}
        for ticker in self.tickers:
            print(f"Fetching data for {ticker}...")
            df = yf.download(ticker, period=self.period, interval=self.interval)
            
            # Handle yfinance MultiIndex columns if multiple tickers were requested at once
            if isinstance(df.columns, pd.MultiIndex):
                # If we download multiple at once, df might be structured differently
                # But here we download one by one for simplicity and robustness
                df.columns = df.columns.droplevel(1)
                
            df.dropna(inplace=True)
            if not df.empty:
                data_map[ticker] = df
                
        return data_map
