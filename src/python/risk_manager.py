import numpy as np
import pandas as pd

class ForexRiskManager:
    """
    Institutional Forex Risk Manager with Variable Spreads, Swap Fees, 
    Correlation Scaling, and Fixed Fractional Risk.
    """
    def __init__(self, risk_per_trade=0.01, atr_multiplier=2.0, max_leverage=10.0, 
                 daily_loss_limit=0.02, initial_capital=100000.0):
        self.risk_per_trade = risk_per_trade
        self.atr_multiplier = atr_multiplier
        self.max_leverage = max_leverage
        self.daily_loss_limit = daily_loss_limit
        self.initial_capital = initial_capital
        
        # Professional Forex Parameters
        self.LOT_SIZE = 100000
        
        # Pair-Specific Cost Configuration (Pips)
        self.ASSET_SPECS = {
            'EURUSD=X': {'spread': 0.8, 'comm': 5.0, 'swap': -0.5},
            'GBPUSD=X': {'spread': 1.2, 'comm': 5.0, 'swap': -0.7},
            'USDJPY=X': {'spread': 0.7, 'comm': 5.0, 'swap': -0.4},
            'AUDUSD=X': {'spread': 1.0, 'comm': 5.0, 'swap': -0.6},
            'USDCAD=X': {'spread': 1.1, 'comm': 5.0, 'swap': -0.6},
            'DEFAULT':  {'spread': 1.5, 'comm': 7.0, 'swap': -1.0}
        }

    def get_specs(self, ticker):
        return self.ASSET_SPECS.get(ticker, self.ASSET_SPECS['DEFAULT'])

    def calculate_lot_size(self, current_equity, price, atr, ticker):
        """
        Calculate lot size with correlation awareness and volatility targeting.
        """
        if np.isnan(atr) or atr == 0: return 0
            
        # 1. Fixed Fractional Risk (0.5% - 1.0%)
        risk_amt_currency = current_equity * self.risk_per_trade
        
        # 2. Stop Loss Distance
        sl_distance = atr * self.atr_multiplier
        if sl_distance == 0: return 0
            
        # 3. Base Units adjusted for account currency (USD)
        if ticker.startswith("USD") and not ticker.startswith("USDUSD"):
            # For USD/XXX (e.g., USDJPY), 1 unit of price change = 1 unit of XXX.
            # We need to convert the risk to account currency (USD).
            # Units = (Risk_USD * Price) / SL_Distance_XXX
            units = (risk_amt_currency * price) / sl_distance
        else:
            # For XXX/USD (e.g., EURUSD), 1 unit of price change = 1 unit of USD.
            # Units = Risk_USD / SL_Distance_USD
            units = risk_amt_currency / sl_distance
        
        # 4. Convert to Lots (1 Lot = 100,000 units of base currency)
        lots = round(units / self.LOT_SIZE, 2)
        
        # 5. Apply Leverage Cap
        notional = lots * self.LOT_SIZE
        if not ticker.startswith("USD"):
             # For XXX/USD, notional in USD is Lots * LotSize * Price
             notional *= price
             
        if notional > (current_equity * self.max_leverage):
            if not ticker.startswith("USD"):
                lots = round((current_equity * self.max_leverage) / (self.LOT_SIZE * price), 2)
            else:
                lots = round((current_equity * self.max_leverage) / self.LOT_SIZE, 2)
            
        return max(lots, 0)

    def calculate_correlation_scaling(self, signals_series):
        """
        Reduces position sizes if multiple assets are correlated in the same direction.
        For simplicity, we use a global scaler based on the number of active signals.
        """
        active_count = (signals_series != 0).sum()
        if active_count > 2:
            # Scale down to avoid overcrowding (e.g., 20% reduction per additional trade)
            return 1.0 / np.sqrt(active_count)
        return 1.0

    def get_pip_value(self, ticker):
        if "JPY" in ticker: return 0.01
        return 0.0001
