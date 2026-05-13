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
        
        # 1. Calculate Correlation Scaling factor across the portfolio
        all_signals = pd.concat([df['Signal'] for df in self.data_map.values()], axis=1)
        corr_scaler = all_signals.apply(self.risk_manager.calculate_correlation_scaling, axis=1)
        
        asset_pnl = []
        
        for ticker, df in self.data_map.items():
            specs = self.risk_manager.get_specs(ticker)
            pip_val = self.risk_manager.get_pip_value(ticker)
            
            # Base Signal (Shifted)
            df['Raw_Signal'] = df['Signal'].shift(1).fillna(0)
            
            # Dynamic Lot Sizing with Correlation Penalty
            # Units = (Risk / (ATR * Multiplier)) * Corr_Scaler
            df['Lots'] = (self.initial_capital * self.risk_manager.risk_per_trade) / \
                         (df['ATR_14'] * self.risk_manager.atr_multiplier * self.risk_manager.LOT_SIZE)
            
            df['Lots'] = (df['Lots'] * df['Raw_Signal'].abs() * corr_scaler).round(2).fillna(0)
            
            # 2. PnL Calculation
            df['Price_Diff'] = df['Close'] - df['Close'].shift(1)
            df['Gross_PnL'] = df['Raw_Signal'] * df['Price_Diff'] * df['Lots'] * self.risk_manager.LOT_SIZE
            
            # 3. TRANSACTION COSTS (FRICTION)
            df['Trade_Event'] = df['Lots'].diff().abs() > 0
            
            # a) Commissions (Charged on every trade change)
            df['Commission_Cost'] = (df['Lots'].diff().abs()) * specs['comm']
            
            # b) Variable Spreads (Charged on entry and exit)
            df['Spread_Cost'] = (df['Lots'].diff().abs()) * (specs['spread'] * pip_val) * self.risk_manager.LOT_SIZE
            
            # c) Slippage Modeling (Random noise between 0.1 and 0.5 pips per trade)
            np.random.seed(42)
            slippage_pips = np.random.uniform(0.1, 0.5, size=len(df))
            df['Slippage_Cost'] = (df['Lots'].diff().abs()) * (slippage_pips * pip_val) * self.risk_manager.LOT_SIZE
            
            # d) Swap / Rollover Fees (Daily cost for holding a position)
            # Only charged if we hold a position (Signal != 0)
            df['Swap_Cost'] = (df['Lots'] > 0).astype(int) * (abs(specs['swap']) * pip_val) * self.risk_manager.LOT_SIZE
            
            # 4. Net PnL
            df['Net_PnL'] = df['Gross_PnL'] - df['Commission_Cost'] - df['Spread_Cost'] - df['Slippage_Cost'] - df['Swap_Cost']
            
            asset_pnl.append(df['Net_PnL'].rename(ticker))
            
        # Combine all asset PnLs
        portfolio_pnl = pd.concat(asset_pnl, axis=1).fillna(0)
        self.portfolio_df = pd.DataFrame(index=portfolio_pnl.index)
        self.portfolio_df['Daily_PnL'] = portfolio_pnl.sum(axis=1)
        self.portfolio_df['Strategy_Return'] = self.portfolio_df['Daily_PnL'] / self.initial_capital
        
        # Cumulative Equity
        self.portfolio_df['Strategy_Equity'] = self.initial_capital + self.portfolio_df['Daily_PnL'].cumsum()
        
        return self.portfolio_df
        
    def calculate_metrics(self):
        strat_returns = self.portfolio_df['Strategy_Return'].dropna()
        if len(strat_returns) == 0: return {"Error": "No returns"}

        total_pnl = self.portfolio_df['Daily_PnL'].sum()
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
