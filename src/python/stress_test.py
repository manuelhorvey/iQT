import numpy as np
import pandas as pd
from scipy.stats import norm

class StressTester:
    """
    Institutional Stress Testing Suite for Quantitative Strategies.
    Includes Monte Carlo, Deflated Sharpe, and Correlation Shock modules.
    """
    def __init__(self, portfolio_returns, initial_capital=100000.0):
        self.returns = portfolio_returns # Daily returns series
        self.initial_capital = initial_capital

    def run_monte_carlo(self, n_sims=10000):
        """Simulates 10,000 paths using block bootstrap to preserve autocorrelation."""
        print(f"Running {n_sims} Monte Carlo paths...")
        sim_results = []
        n_days = len(self.returns)
        
        for _ in range(n_sims):
            # Block Bootstrap (Block size 5)
            block_size = 5
            indices = np.arange(n_days - block_size)
            sampled_indices = np.random.choice(indices, size=n_days // block_size, replace=True)
            
            path_returns = []
            for idx in sampled_indices:
                path_returns.extend(self.returns.iloc[idx:idx+block_size])
            
            # Calculate final equity for this path
            path_returns = np.array(path_returns)
            final_val = self.initial_capital * np.prod(1 + path_returns)
            sim_results.append(final_val)
            
        return {
            'mc_mean_equity': np.mean(sim_results),
            'mc_median_equity': np.median(sim_results),
            'mc_95th_percentile': np.percentile(sim_results, 95),
            'mc_5th_percentile': np.percentile(sim_results, 5),
            'prob_of_loss': (np.array(sim_results) < self.initial_capital).mean()
        }

    def calculate_var(self, confidence=0.95):
        """Calculates Value at Risk (VaR)."""
        mu = self.returns.mean()
        sigma = self.returns.std()
        var = norm.ppf(1 - confidence, mu, sigma)
        return var * self.initial_capital

    def calculate_deflated_sharpe(self, n_trials=50):
        """
        Calculates the Deflated Sharpe Ratio (DSR).
        Penalizes the Sharpe for multiple testing bias.
        """
        sharpe = (self.returns.mean() * 252) / (self.returns.std() * np.sqrt(252))
        
        # Simple DSR approximation (Bailey and Lopez de Prado)
        # Adjusts for the number of backtest trials performed
        emc = 0.5772156649 # Euler-Mascheroni constant
        expected_max_sharpe = np.sqrt(2 * np.log(n_trials)) - (emc + np.log(2) / 2) / np.sqrt(2 * np.log(n_trials))
        
        # If observed sharpe > expected max, the strategy has 'alpha'
        is_significant = sharpe > expected_max_sharpe
        
        return {
            'observed_sharpe': sharpe,
            'dsr_threshold': expected_max_sharpe,
            'is_statistically_significant': is_significant
        }

    def correlation_shock_test(self, asset_returns_df):
        """
        Simulates a 'Correlation Cluster' where all assets move together.
        Measures the impact on HRP weights and Drawdown.
        """
        # Force correlation to 0.9
        mean_rets = asset_returns_df.mean()
        std_rets = asset_returns_df.std()
        
        # Generate synthetic shocked returns
        market_factor = np.random.normal(0, 1, size=len(asset_returns_df))
        shocked_data = {}
        for col in asset_returns_df.columns:
            # 90% correlation with market factor
            shocked_data[col] = 0.9 * market_factor + 0.1 * np.random.normal(0, 1, size=len(asset_returns_df))
            shocked_data[col] = shocked_data[col] * std_rets[col] + mean_rets[col]
            
        shocked_df = pd.DataFrame(shocked_data)
        return shocked_df.corr().mean().mean() # Average correlation after shock
