import numpy as np
import pandas as pd

class MultiAssetBacktester:
    def __init__(self, data_map, initial_capital=100000.0, risk_manager=None):
        self.data_map = data_map
        self.initial_capital = initial_capital
        self.risk_manager = risk_manager
        self.portfolio_df = None
        
    def run(self):
        print(f"Running Institutional-Grade Forex Backtest for {len(self.data_map)} pairs...")
        
        # 1. Calculate Rolling HRP Weights across the portfolio
        returns_df = pd.DataFrame({ticker: df['Returns'] for ticker, df in self.data_map.items()}).fillna(0)
        
        # Pre-allocate HRP weights dataframe
        hrp_weights_df = pd.DataFrame(index=returns_df.index, columns=returns_df.columns)
        
        print("Calculating rolling HRP allocations (this may take a moment)...")
        from allocation import HRPAllocator
        for i in range(252, len(returns_df)):
            window = returns_df.iloc[i-252:i]
            allocator = HRPAllocator(window)
            hrp_weights_df.iloc[i] = allocator.get_weights()
        
        # Fill initial weights with equal weight
        hrp_weights_df.iloc[:252] = 1.0 / len(self.data_map)
        
        # --- Institutional Stability: Weight Smoothing (EMA 20) ---
        # Prevents rapid allocation flips that erode alpha via rebalancing costs
        hrp_weights_df = hrp_weights_df.ffill().ewm(span=20).mean()
        
        asset_pnl = []
        
        for ticker, df in self.data_map.items():
            specs = self.risk_manager.get_specs(ticker)
            pip_val = self.risk_manager.get_pip_value(ticker)
            
            # Pre-calculate Lots for the loop
            df['Base_Lots'] = (self.initial_capital * self.risk_manager.risk_per_trade) / \
                             (df['ATR_14'] * self.risk_manager.atr_multiplier * self.risk_manager.LOT_SIZE)
            hrp_scale = hrp_weights_df[ticker] * len(self.data_map)
            df['Lots'] = (df['Base_Lots'] * hrp_scale).round(2).fillna(0)
            
            # 2. PATH-DEPENDENT BACKTEST (Iterative)
            net_pnl = np.zeros(len(df))
            current_pos = 0 
            entry_price = 0
            sl, tp, lots, bars_held = 0, 0, 0, 0
            
            for i in range(1, len(df)):
                row = df.iloc[i]
                prev_signal = df.iloc[i-1]['Signal']
                
                # Exit Logic (Path Dependent)
                if current_pos != 0:
                    bars_held += 1
                    hit_exit = False
                    exit_price = row['Close']
                    
                    # --- Institutional: Relaxed Break-Even Logic ---
                    # Only move to BE if profit >= 1.5 ATR (matching tightest stop)
                    # Adjust SL to Entry + Costs to be truly net-zero
                    cost_in_pips = specs['spread'] + (specs['comm'] / (pip_val * self.risk_manager.LOT_SIZE * lots))
                    
                    profit_pips = (row['High'] - entry_price) if current_pos == 1 else (entry_price - row['Low'])
                    if profit_pips > (vol * 1.5): 
                        sl = entry_price + (current_pos * cost_in_pips * pip_val) # Truly Risk-Free
                    
                    if current_pos == 1:
                        if row['Low'] < sl: exit_price = sl; hit_exit = True
                        elif row['High'] > tp: exit_price = tp; hit_exit = True
                        elif prev_signal != 1 or bars_held >= 10: hit_exit = True
                    elif current_pos == -1:
                        if row['High'] > sl: exit_price = sl; hit_exit = True
                        elif row['Low'] < tp: exit_price = tp; hit_exit = True
                        elif prev_signal != -1 or bars_held >= 10: hit_exit = True
                            
                    if hit_exit:
                        pnl = (exit_price - entry_price) * current_pos * lots * self.risk_manager.LOT_SIZE
                        # Subtract Exit Costs (Spread + Slippage + Commission)
                        cost = (specs['spread'] * pip_val * self.risk_manager.LOT_SIZE * lots) + \
                               (specs['comm'] * lots) + \
                               (0.5 * pip_val * self.risk_manager.LOT_SIZE * lots) # Slippage
                        net_pnl[i] = pnl - cost
                        current_pos = 0
                        bars_held = 0
                
                # Entry Logic
                if current_pos == 0 and prev_signal != 0:
                    current_pos = int(prev_signal)
                    entry_price = row['Open']
                    lots = df.iloc[i-1]['Lots']
                    bars_held = 0
                    vol = row['ATR_14']
                    
                    # --- Institutional: Adaptive Stop & Dynamic RR ---
                    prob = df.iloc[i-1]['Signal_Prob']
                    regime = df.iloc[i-1]['Regime_Label']
                    
                    sl_mult = self.risk_manager.calculate_adaptive_sl_multiplier(prob, regime)
                    dynamic_rr = self.risk_manager.calculate_dynamic_rr(prob, regime, ticker)
                    
                    sl = entry_price - (current_pos * sl_mult * vol)
                    tp = entry_price + (current_pos * sl_mult * vol * dynamic_rr) 
                    
                    # Subtract Entry Costs
                    cost = (specs['spread'] * pip_val * self.risk_manager.LOT_SIZE * lots) + \
                           (specs['comm'] * lots)
                    net_pnl[i] -= cost
                
                # Daily Mark-to-Market (Optional for visualization, but net_pnl handles realized)
                
            df['Net_PnL'] = net_pnl
            asset_pnl.append(df['Net_PnL'].rename(ticker))
            
        # Combine all asset PnLs
        portfolio_pnl = pd.concat(asset_pnl, axis=1).fillna(0)
        self.portfolio_df = pd.DataFrame(index=portfolio_pnl.index)
        self.portfolio_df['Daily_PnL'] = portfolio_pnl.sum(axis=1)
        
        # --- Institutional Tail Risk Model ---
        # Simulate Weekend Gaps & News Slippage (0.5% hit every 20 bars if active)
        tail_risk = np.zeros(len(self.portfolio_df))
        active_mask = (self.portfolio_df['Daily_PnL'] != 0)
        tail_risk[active_mask & (np.arange(len(self.portfolio_df)) % 20 == 0)] = self.initial_capital * 0.005
        self.portfolio_df['Tail_Risk_Cost'] = tail_risk
        
        self.portfolio_df['Net_Daily_PnL'] = self.portfolio_df['Daily_PnL'] - self.portfolio_df['Tail_Risk_Cost']
        self.portfolio_df['Strategy_Return'] = self.portfolio_df['Net_Daily_PnL'] / self.initial_capital
        
        # Cumulative Equity
        self.portfolio_df['Strategy_Equity'] = self.initial_capital + self.portfolio_df['Net_Daily_PnL'].cumsum()
        
        return self.portfolio_df
        
    def calculate_metrics(self):
        strat_returns = self.portfolio_df['Strategy_Return'].dropna()
        if len(strat_returns) == 0: return {"Error": "No returns"}

        total_pnl = self.portfolio_df['Net_Daily_PnL'].sum()
        total_return = total_pnl / self.initial_capital
        
        annualized_return = strat_returns.mean() * 252
        annualized_vol = strat_returns.std() * np.sqrt(252)
        sharpe_ratio = annualized_return / annualized_vol if annualized_vol != 0 else 0
        
        # Max Drawdown
        cum_equity = self.portfolio_df['Strategy_Equity']
        running_max = cum_equity.cummax()
        drawdown = (cum_equity - running_max) / running_max
        max_drawdown = drawdown.min()
        
        metrics = {
            'Total PnL': f"${total_pnl:,.2f}",
            'Total Return': f"{total_return:.2%}",
            'Annualized Return': f"{annualized_return:.2%}",
            'Annualized Volatility': f"{annualized_vol:.2%}",
            'Sharpe Ratio': f"{sharpe_ratio:.2f}",
            'Max Drawdown': f"{max_drawdown:.2%}",
        }
        
        return metrics
