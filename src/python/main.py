import argparse
from data_loader import DataLoader
from features import FeatureEngineer
from regime import RegimeDetector
from ensemble import EnsembleModel
from backtester import MultiAssetBacktester
from dashboard_generator import DashboardGenerator
from optimization import WalkForwardOptimizer
from risk_manager import ForexRiskManager
from live_signals import LiveSignalEngine
from bridge import SignalPublisher
from stress_test import StressTester
import pandas as pd

def main():
    parser = argparse.ArgumentParser(description='Run Quant Research Pipeline')
    parser.add_argument('--tickers', type=str, default='EURUSD=X,GBPUSD=X,USDJPY=X,AUDUSD=X,USDCAD=X', help='Comma-separated list of tickers.')
    parser.add_argument('--period', type=str, default='5y', help='Data period to fetch.')
    parser.add_argument('--risk_per_trade', type=float, default=0.005, help='Equity risk per trade (e.g., 0.005 for 0.5%).')
    parser.add_argument('--mode', type=str, default='backtest', choices=['backtest', 'live'], help='Execution mode.')
    parser.add_argument('--threshold', type=int, default=65, help='Confidence threshold (50-100).')
    parser.add_argument('--stress_test', action='store_true', help='Run institutional stress testing suite.')
    args = parser.parse_args()

    tickers = [t.strip() for t in args.tickers.split(',')]
    threshold_decimal = args.threshold / 100.0

    print("=" * 50)
    print(f"Starting Institutional Forex Pipeline | MODE: {args.mode.upper()}")
    print(f"Pairs: {', '.join(tickers)} | THRESHOLD: {args.threshold}%")
    print("=" * 50)

    # 1. Load Data
    # For live mode, we might want a shorter period but 5y is fine for training
    loader = DataLoader(tickers=tickers, period=args.period)
    data_map = loader.fetch_data()

    # 2. Pre-process (Features + Regimes)
    processed_data = {}
    for ticker, df in data_map.items():
        print(f"\nProcessing {ticker}...")
        engineer = FeatureEngineer(df)
        df = engineer.generate_features()
        detector = RegimeDetector()
        df = detector.fit_predict(df)
        processed_data[ticker] = df

    # 3. Train Ensemble Model
    ensemble = EnsembleModel()
    X, y, feature_cols = ensemble.prepare_multi_asset_data(processed_data)
    ensemble.train(X, y)

    # 4. Generate Signals
    signaled_data = {}
    for ticker, df in processed_data.items():
        df = ensemble.generate_signals(df, feature_cols, calculate_shap=True, threshold=threshold_decimal)
        signaled_data[ticker] = df

    # 5. Initialize Risk Manager
    risk_manager = ForexRiskManager(risk_per_trade=args.risk_per_trade)

    if args.mode == 'backtest':
        # 6. Portfolio Backtest
        backtester = MultiAssetBacktester(signaled_data, risk_manager=risk_manager)
        portfolio_res = backtester.run()
        metrics = backtester.calculate_metrics()

        # 7. Generate Research Dashboard
        dashboard = DashboardGenerator(tickers[0], signaled_data[tickers[0]], metrics, feature_cols=feature_cols)
        dashboard.generate()

        print("\n" + "=" * 50)
        print("PORTFOLIO BACKTEST RESULTS (FOREX)")
        print("=" * 50)
        for k, v in metrics.items():
            print(f"{k}: {v}")
            
        if args.stress_test:
            print("\n" + "=" * 50)
            print("INSTITUTIONAL STRESS TEST RESULTS")
            print("=" * 50)
            tester = StressTester(portfolio_res['Strategy_Return'])
            
            # Monte Carlo
            mc_res = tester.run_monte_carlo(n_sims=5000)
            print(f"MC Mean Equity: ${mc_res['mc_mean_equity']:,.2f}")
            print(f"MC 5th Percentile (Value at Risk): ${mc_res['mc_5th_percentile']:,.2f}")
            print(f"Prob of Portfolio Loss: {mc_res['prob_of_loss']:.1%}")
            
            # Deflated Sharpe
            dsr_res = tester.calculate_deflated_sharpe(n_trials=100)
            print(f"Observed Sharpe: {dsr_res['observed_sharpe']:.2f}")
            print(f"DSR Significance Threshold: {dsr_res['dsr_threshold']:.2f}")
            print(f"Statistically Significant: {dsr_res['is_statistically_significant']}")
            
            # VaR
            var_95 = tester.calculate_var(0.95)
            print(f"1-Day VaR (95%): ${abs(var_95):,.2f}")
    
    elif args.mode == 'live':
        # 6. Live Signal Generation
        print("\n" + "=" * 50)
        print("GENERATING LIVE EXECUTION TICKETS")
        print("=" * 50)
        
        # Initialize ZeroMQ Bridge
        publisher = SignalPublisher()
        
        live_engine = LiveSignalEngine(risk_manager)
        tickets = live_engine.generate_tickets(signaled_data)
        summary = live_engine.get_portfolio_summary(tickets, signaled_data)
        
        # Publish to C++ Engine
        publisher.publish_tickets(tickets)
        
        # 7. Generate Live Dashboard
        dashboard = DashboardGenerator(tickers[0], signaled_data[tickers[0]], {}, feature_cols=feature_cols)
        dashboard.generate_live_dashboard(tickets, summary)
        
        print(f"Active Signals: {summary['active_signals']}")
        print(f"Portfolio Volatility: {summary['portfolio_vol']}")
        print(f"Total Exposure: {summary['total_exposure_lots']} Lots")
        print("\nLive Dashboard Ready!")
        
        import time
        time.sleep(1) # Final flush for ZMQ
        publisher.close()

    print("\nPipeline Complete!")

if __name__ == "__main__":
    main()
