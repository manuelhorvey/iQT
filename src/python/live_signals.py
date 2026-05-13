import pandas as pd
import numpy as np

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
        execution instructions.
        """
        tickets = []
        all_signals = pd.Series({ticker: df['Signal'].iloc[-1] for ticker, df in signaled_data.items()})
        
        # Calculate Global Portfolio Correlation Scaling
        corr_scaler = self.risk_manager.calculate_correlation_scaling(all_signals)
        
        for ticker, df in signaled_data.items():
            latest = df.iloc[-1]
            signal = latest['Signal']
            prob = latest['Signal_Prob']
            price = latest['Close']
            atr = latest['ATR_14']
            
            if signal == 0:
                continue
                
            # 1. Calculate Lot Size with Correlation Penalty
            base_lots = self.risk_manager.calculate_lot_size(self.initial_capital, price, atr, ticker)
            final_lots = round(base_lots * corr_scaler, 2)
            
            # 2. Calculate Execution Levels
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
                'corr_penalty': f"{ (1-corr_scaler)*100 :.0f}%" if corr_scaler < 1.0 else "None"
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
