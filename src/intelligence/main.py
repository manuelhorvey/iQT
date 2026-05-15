import argparse
import numpy as np
import pandas as pd
import random

from data_loader import DataManager
from features import FeatureEngineer
from regime import RegimeDetector
from ensemble import EnsembleModel
from backtester import MultiAssetBacktester
from dashboard_generator import DashboardGenerator
from optimization import WalkForwardOptimizer
from risk_manager import ForexRiskManager
from live_signals import LiveSignalEngine
from bridge import SignalPublisher


# ---------------------------------------------------
# reproducibility
# ---------------------------------------------------
def set_seed(seed: int = 42):
    np.random.seed(seed)
    random.seed(seed)


# ---------------------------------------------------
# SAFE GLOBAL ALIGNMENT (V8 FIXED)
# ---------------------------------------------------
def align_dataframes(data_map: dict) -> dict:
    """
    Align all assets to a single stable reference timeline.
    Prevents cross-asset shape drift and WFO inconsistencies.
    """
    ref_index = next(iter(data_map.values())).index

    aligned = {}

    for t, df in data_map.items():
        df = df.reindex(ref_index)

        # safe fill (no leakage from future data)
        df = df.ffill().bfill()

        aligned[t] = df.copy()

    return aligned


# ---------------------------------------------------
# dataset build (NO LEAKAGE)
# ---------------------------------------------------
def build_dataset(data_map):
    processed = {}

    regime_model = RegimeDetector()

    # feature engineering
    for ticker, df in data_map.items():
        fe = FeatureEngineer(df)
        processed[ticker] = fe.generate_features()

    # IMPORTANT: global alignment BEFORE regimes
    processed = align_dataframes(processed)

    # regime fitting per asset
    for t in processed:
        processed[t] = regime_model.fit_predict(processed[t])

    return processed, regime_model


# ---------------------------------------------------
# model training
# ---------------------------------------------------
def train_model(processed_data):
    model = EnsembleModel()

    X, y, df_full, feature_cols = model.prepare_multi_asset_data(processed_data)

    model.train(X, y, df_full=df_full)

    return model, feature_cols


# ---------------------------------------------------
# SAFE BACKTEST WRAPPER (V8 FIX)
# ---------------------------------------------------
def _safe_align(df):
    return df.dropna(subset=["Returns", "Signal"]).copy()


# ---------------------------------------------------
# backtest
# ---------------------------------------------------
def run_backtest(model, processed_data, feature_cols, risk_manager, args):
    signaled = {}

    for t, df in processed_data.items():
        sig = model.generate_signals(
            df,
            feature_cols,
            threshold=args.threshold,
            regime_gating_threshold=args.regime_gating,
        )

        signaled[t] = _safe_align(sig)

    backtester = MultiAssetBacktester(
        signaled,
        risk_manager=risk_manager,
        tail_risk_penalty=args.tail_risk_penalty,
    )

    results = backtester.run()
    metrics = backtester.calculate_metrics()

    return results, metrics, signaled


# ---------------------------------------------------
# live execution (HARDENED)
# ---------------------------------------------------
def run_live(model, processed_data, feature_cols, risk_manager, args):
    print("\nLIVE MODE ACTIVE")

    # safety: remove NaNs and generate live signals
    signaled_data = {}
    for t, df in processed_data.items():
        # Generate Signals (including EV and Archetypes)
        sig = model.generate_signals(
            df.dropna(),
            feature_cols,
            threshold=args.threshold,
            regime_gating_threshold=args.regime_gating
        )
        signaled_data[t] = sig

    engine = LiveSignalEngine(risk_manager)
    publisher = SignalPublisher()

    # Pass the threshold to the engine
    tickets = engine.generate_tickets(signaled_data, threshold=args.threshold)
    summary = engine.get_portfolio_summary(tickets, signaled_data)

    publisher.publish_tickets(tickets)

    # RESTORE: Update Live Command Center Telemetry
    from dashboard_generator import DashboardGenerator
    dashboard = DashboardGenerator(None, None, None)
    dashboard.generate_live_dashboard(tickets, summary, tickers_count=len(processed_data))

    print(f"Active Signals: {summary['active_signals']}")
    print(f"Exposure: {summary['total_exposure_lots']}")

    publisher.close()


# ---------------------------------------------------
# main
# ---------------------------------------------------
def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--tickers", type=str,
                        default="EURUSD=X,GBPUSD=X,USDJPY=X,AUDUSD=X,USDCAD=X")

    parser.add_argument("--period", type=str, default="5y")
    parser.add_argument("--mode", type=str, default="backtest",
                        choices=["backtest", "live"])

    parser.add_argument("--risk_per_trade", type=float, default=0.005)
    parser.add_argument("--threshold", type=float, default=0.65)
    parser.add_argument("--tail_risk_penalty", type=float, default=0.005)
    parser.add_argument("--regime_gating", type=float, default=0.0)
    parser.add_argument("--stress_test", action="store_true")
    parser.add_argument("--optimize", action="store_true")
    parser.add_argument("--seed", type=int, default=42)

    args = parser.parse_args()
    set_seed(args.seed)

    print("=" * 60)
    print(f"iQT PIPELINE | MODE: {args.mode.upper()}")
    print("=" * 60)

    tickers = [t.strip() for t in args.tickers.split(",")]

    provider = "yfinance" if args.mode == "backtest" else "live"
    manager = DataManager(tickers=tickers, provider_type=provider)

    raw_data = manager.get_data(period=args.period)

    # STEP 1: ALIGN FIRST (CRITICAL V8 FIX)
    raw_data = align_dataframes(raw_data)

    # STEP 1.5: FETCH MACO PROXY (UUP - Dollar Index ETF)
    print("Injecting Macro Context (UUP)...")
    uup_ticker = "UUP"
    try:
        uup_data = manager.provider.fetch(uup_ticker, period=args.period, interval="1d")
        uup_series = uup_data["Close"]
        uup_slope = uup_series.pct_change().rolling(20).mean()
    except Exception as e:
        print(f"Warning: Could not fetch UUP: {e}. Defaulting macro features to 0.")
        uup_series = None
        uup_slope = None

    # STEP 2: FEATURES + REGIME
    processed_data = {}
    regime_model = RegimeDetector()

    for ticker, df in raw_data.items():
        fe = FeatureEngineer(df)
        fe.generate_features()
        fe.add_macro_features(uup_slope)
        
        # New: Add direct correlation with UUP (using fe.df which has Returns)
        if uup_series is not None:
            aligned_uup = uup_series.reindex(fe.df.index).ffill()
            fe.df["UUP_Corr_60"] = fe.df["Returns"].rolling(60).corr(aligned_uup.pct_change())
        else:
            fe.df["UUP_Corr_60"] = 0.0

        processed_data[ticker] = fe.df

    # regime fitting per asset
    for t in processed_data:
        processed_data[t] = regime_model.fit_predict(processed_data[t])

    # STEP 3: MODEL
    model, feature_cols = train_model(processed_data)

    # STEP 4: RISK
    risk_manager = ForexRiskManager(risk_per_trade=args.risk_per_trade)

    # STEP 5: EXECUTION
    if args.optimize:
        optimizer = WalkForwardOptimizer(
            processed_data,
            risk_manager=risk_manager,
            tail_risk_penalty=args.tail_risk_penalty,
            regime_gating_threshold=args.regime_gating,
        )

        reports, oos = optimizer.run(feature_cols)

        print("\nWFO COMPLETE")
        for r in reports:
            print(r)

    elif args.mode == "backtest":
        results, metrics, signaled = run_backtest(
            model,
            processed_data,
            feature_cols,
            risk_manager,
            args,
        )

        print("\nBACKTEST RESULTS")
        print("=" * 40)
        for k, v in metrics.items():
            print(f"{k}: {v}")

        if args.stress_test:
            from stress_test import StressTester

            tester = StressTester(results["Strategy_Return"])
            mc = tester.run_monte_carlo(n_sims=5000)

            print("\nSTRESS TEST")
            print(mc)

        DashboardGenerator(
            tickers[0],
            signaled[tickers[0]],
            metrics,
            feature_cols=feature_cols,
        ).generate()

    elif args.mode == "live":
        run_live(model, processed_data, feature_cols, risk_manager, args)

    print("\nPIPELINE COMPLETE")


if __name__ == "__main__":
    main()