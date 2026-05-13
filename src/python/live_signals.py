import pandas as pd
import numpy as np
from allocation import HRPAllocator

class LiveSignalEngine:
    """
    Translates raw model signals and risk parameters into actionable 
    Forex execution tickets.
    """
    def __init__(self, risk_manager, initial_capital=100000.0):
        self.risk_manager = risk_manager
        self.initial_capital = initial_capital

    def generate_tickets(self, signaled_data):
        """
        Processes the latest data point for each pair and generates 
        execution instructions using HRP allocation.
        """
        # 1. Calculate HRP Weights
        returns_df = pd.DataFrame({ticker: df['Returns'] for ticker, df in signaled_data.items()}).dropna()
        allocator = HRPAllocator(returns_df)
        hrp_weights = allocator.get_weights()
        
        tickets = []
        for ticker, df in signaled_data.items():
            latest = df.iloc[-1]
            signal = latest['Signal']
            prob = latest['Signal_Prob']
            price = latest['Close']
            atr = latest['ATR_14']
            
            if signal == 0:
                continue
                
            # 2. Calculate Lot Size with HRP Scaling
            base_lots = self.risk_manager.calculate_lot_size(self.initial_capital, price, atr, ticker)
            final_lots = round(base_lots * (hrp_weights[ticker] * len(hrp_weights)), 2) # Normalized HRP
            
            # 3. Calculate Execution Levels
            sl_distance = atr * self.risk_manager.atr_multiplier
            pip_val = self.risk_manager.get_pip_value(ticker)
            
            stop_loss = price - sl_distance if signal == 1 else price + sl_distance
            take_profit = price + (sl_distance * 2) if signal == 1 else price - (sl_distance * 2)
            
            # 3. Conviction Label
            conviction = "STRONG" if prob > 0.7 or prob < 0.3 else "MODERATE"
            
            tickets.append({
                'ticker': ticker,
                'regime': latest['Regime_Label'],
                'signal': 'BUY' if signal == 1 else 'SELL',
                'conviction': conviction,
                'confidence': f"{prob*100:.1f}%",
                'price': price,
                'lots': final_lots,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'sl_pips': round(sl_distance / pip_val, 1),
                'risk_reward': "1:2",
                'hrp_scale': f"{ (hrp_weights[ticker] * len(hrp_weights)) * 100 :.0f}%"
            })
            
        return tickets

    def get_portfolio_summary(self, tickets, signaled_data):
        """Calculates aggregate portfolio-level risk metrics."""
        total_lots = sum(t['lots'] for t in tickets)
        active_pairs = len(tickets)
        
        # Estimate Portfolio Volatility based on average ATR
        avg_vol = np.mean([df['Returns'].std() * np.sqrt(252) for df in signaled_data.values()])
        
        summary = {
            'active_signals': active_pairs,
            'total_exposure_lots': round(total_lots, 2),
            'portfolio_vol': f"{avg_vol*100:.2f}%",
            'max_risk_per_trade': f"{self.risk_manager.risk_per_trade*100:.1f}%",
            'highest_conviction': tickets[0]['ticker'] if tickets else "N/A"
        }
        return summary
