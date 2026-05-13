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
        
        # Professional Forex Parameters (Hardened for Reality)
        self.LOT_SIZE = 100000
        
        # Pair-Specific Cost Configuration (Pips) - Institutional Grade
        self.ASSET_SPECS = {
            # Majors
            'EURUSD=X': {'spread': 0.8, 'comm': 7.0, 'swap': -0.5},
            'GBPUSD=X': {'spread': 1.2, 'comm': 7.0, 'swap': -0.7},
            'USDJPY=X': {'spread': 0.7, 'comm': 7.0, 'swap': -0.4},
            'AUDUSD=X': {'spread': 0.9, 'comm': 7.0, 'swap': -0.6},
            'USDCAD=X': {'spread': 1.1, 'comm': 7.0, 'swap': -0.6},
            'NZDUSD=X': {'spread': 1.2, 'comm': 7.0, 'swap': -0.5},
            'USDCHF=X': {'spread': 1.3, 'comm': 7.0, 'swap': -0.8},
            
            # Euro Crosses
            'EURGBP=X': {'spread': 1.4, 'comm': 7.0, 'swap': -0.6},
            'EURJPY=X': {'spread': 1.2, 'comm': 7.0, 'swap': -0.5},
            'EURAUD=X': {'spread': 1.8, 'comm': 7.0, 'swap': -0.8},
            'EURCAD=X': {'spread': 1.7, 'comm': 7.0, 'swap': -0.7},
            'EURCHF=X': {'spread': 1.6, 'comm': 7.0, 'swap': -0.9},
            'EURNZD=X': {'spread': 2.4, 'comm': 7.0, 'swap': -1.1},
            
            # Pound Crosses
            'GBPJPY=X': {'spread': 1.9, 'comm': 7.0, 'swap': -0.8},
            'GBPAUD=X': {'spread': 2.5, 'comm': 7.0, 'swap': -1.2},
            'GBPCAD=X': {'spread': 2.2, 'comm': 7.0, 'swap': -0.9},
            'GBPCHF=X': {'spread': 2.1, 'comm': 7.0, 'swap': -1.1},
            'GBPNZD=X': {'spread': 2.8, 'comm': 7.0, 'swap': -1.4},
            
            # Yen Crosses
            'AUDJPY=X': {'spread': 1.3, 'comm': 7.0, 'swap': -0.6},
            'CADJPY=X': {'spread': 1.4, 'comm': 7.0, 'swap': -0.5},
            'CHFJPY=X': {'spread': 1.6, 'comm': 7.0, 'swap': -0.7},
            'NZDJPY=X': {'spread': 1.7, 'comm': 7.0, 'swap': -0.6},
            
            # Other Minors
            'AUDCAD=X': {'spread': 1.6, 'comm': 7.0, 'swap': -0.7},
            'AUDCHF=X': {'spread': 1.5, 'comm': 7.0, 'swap': -0.8},
            'AUDNZD=X': {'spread': 2.1, 'comm': 7.0, 'swap': -1.0},
            'CADCHF=X': {'spread': 1.6, 'comm': 7.0, 'swap': -0.8},
            'NZDCAD=X': {'spread': 1.9, 'comm': 7.0, 'swap': -0.7},
            'NZDCHF=X': {'spread': 1.8, 'comm': 7.0, 'swap': -0.9},
            
            # Commodities & Exotics (Optional, but included for scale)
            'XAUUSD=X': {'spread': 2.5, 'comm': 10.0, 'swap': -2.0}, # Gold
            'USDMXN=X': {'spread': 35.0, 'comm': 10.0, 'swap': -5.0},
            'USDTRY=X': {'spread': 80.0, 'comm': 15.0, 'swap': -15.0},
            'USDZAR=X': {'spread': 60.0, 'comm': 12.0, 'swap': -8.0},
            'USDSGD=X': {'spread': 2.0, 'comm': 7.0, 'swap': -1.0},
            'USDHKD=X': {'spread': 4.0, 'comm': 7.0, 'swap': -0.5},
            
            'DEFAULT':  {'spread': 3.0, 'comm': 10.0, 'swap': -2.0}
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

    def calculate_dynamic_rr(self, prob, regime_label, ticker):
        """
        Institutional Dynamic RR Logic:
        - Higher Conviction (Prob > 0.7) -> 'Swing' Mode (3.0+ RR)
        - Lower Conviction (Prob < 0.6) -> 'Intraday' Mode (1.2 - 1.5 RR)
        """
        base_rr = 2.0
        
        # 1. Conviction Multiplier
        if prob > 0.75: base_rr = 3.5  
        elif prob > 0.65: base_rr = 2.5
        elif prob < 0.55: base_rr = 1.2 
        
        # 2. Asset Specific Caps
        specs = self.get_specs(ticker)
        if specs['spread'] > 5.0:
            base_rr = max(base_rr, 3.0) 
            
        return round(base_rr, 2)

    def calculate_adaptive_sl_multiplier(self, prob, regime_label):
        """
        Adjusts the 'breathing room' of a trade.
        - High Conviction -> Wider Stop (2.5x) to catch the full trend.
        - Low Conviction -> Tighter Stop (1.5x) to cut losses fast.
        """
        if prob > 0.75: return 2.5 # Swing
        if prob < 0.55: return 1.5 # Intraday
        return 2.0 # Standard
