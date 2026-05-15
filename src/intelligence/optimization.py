import pandas as pd
import numpy as np
from ensemble import EnsembleModel


class WalkForwardOptimizer:
    def __init__(
        self,
        data_map,
        n_folds=5,
        risk_manager=None,
        tail_risk_penalty: float = 0.0015,
        regime_gating_threshold: float = 0.0,
    ):
        self.data_map = data_map
        self.n_folds = n_folds
        self.risk_manager = risk_manager
        self.tail_risk_penalty = tail_risk_penalty
        self.regime_gating_threshold = regime_gating_threshold

    # ---------------------------------------------------
    # HARD ALIGNMENT (FIXED v4.1)
    # ---------------------------------------------------
    def _align(self, data_map):
        """
        Forces all assets onto a shared index.
        This is the REAL fix for broadcasting bugs.
        """

        # intersection of all timestamps
        common_index = None

        for df in data_map.values():
            idx = df.index
            common_index = idx if common_index is None else common_index.intersection(idx)

        aligned = {}

        for t, df in data_map.items():
            df = df.sort_index()
            df = df.reindex(common_index).fillna(0)
            aligned[t] = df

        return aligned

    # ---------------------------------------------------
    # EV SCORE (stable version)
    # ---------------------------------------------------
    def _ev_score(self, y_true, preds):

        preds = np.asarray(preds)
        y_true = np.asarray(y_true)

        if len(preds) == 0 or len(y_true) == 0:
            return 0.0

        # normalize prediction scale (IMPORTANT FIX)
        preds = (preds - np.mean(preds)) / (np.std(preds) + 1e-9)

        corr = np.corrcoef(preds, y_true)[0, 1]
        corr = 0.0 if np.isnan(corr) else corr

        directional = np.mean((preds > 0) == (y_true > 0))

        return 0.6 * corr + 0.4 * directional

    # ---------------------------------------------------
    # CORE LOOP
    # ---------------------------------------------------
    def run(self, feature_cols):

        print(f"Running EV-aware Walk-Forward Optimization ({self.n_folds} folds)...")

        master = list(self.data_map.keys())[0]
        total_len = len(self.data_map[master])

        fold_reports = []
        all_returns = []

        param_grid = [
            {"max_depth": 3, "n_estimators": 120},
            {"max_depth": 5, "n_estimators": 180},
        ]

        for i in range(self.n_folds):

            mid = int(total_len * (0.6 + 0.3 * (i / self.n_folds)))
            end = int(mid + total_len * 0.08)

            # FIX: align ALL assets BEFORE splitting
            aligned_map = self._align(self.data_map)

            is_map = {t: df.iloc[:mid] for t, df in aligned_map.items()}
            oos_map = {t: df.iloc[mid:end] for t, df in aligned_map.items()}

            if len(oos_map[master]) < 30:
                continue

            print(f"\nFold {i+1}: OOS {len(oos_map[master])} bars")

            best_model = None
            best_score = -np.inf

            # ---------------------------------------------------
            # MODEL SELECTION
            # ---------------------------------------------------
            for params in param_grid:

                model = EnsembleModel(params=params)

                X_is, y_is, df_is, _ = model.prepare_multi_asset_data(is_map)
                model.train(X_is, y_is, df_full=df_is)

                preds = model.model_predict(X_is, df_is)

                score = self._ev_score(y_is.values, preds)

                if score > best_score:
                    best_score = score
                    best_model = model

            # ---------------------------------------------------
            # OOS evaluation (FIXED SAFE PIPELINE)
            # ---------------------------------------------------
            signaled = {}
            total_entries = 0
            fold_returns = []

            for t, df in oos_map.items():

                X_o, y_o, _, f_cols = best_model.prepare_data(df)

                sig = best_model.generate_signals(
                    df,
                    f_cols,
                    cost=self.tail_risk_penalty,
                    threshold=0.65, # Standard default for optimization
                    regime_gating_threshold=self.regime_gating_threshold,
                )

                sig = sig.copy()

                sig["Returns"] = sig.get("Returns", 0).fillna(0)
                sig["Signal"] = sig["Signal"].fillna(0)

                # entry count
                entries = ((sig["Signal"] != 0) & (sig["Signal"].shift(1).fillna(0) == 0)).sum()
                total_entries += int(entries)

                signaled[t] = sig

                # SAFE return calc
                fold_returns.append((sig["Returns"].values * sig["Signal"].values))

            # ---------------------------------------------------
            # BACKTEST
            # ---------------------------------------------------
            from backtester import MultiAssetBacktester

            backtester = MultiAssetBacktester(
                signaled,
                risk_manager=self.risk_manager,
                tail_risk_penalty=self.tail_risk_penalty,
            )

            bt = backtester.run()
            metrics = backtester.calculate_metrics()

            all_returns.append(bt["Strategy_Return"])

            fold_reports.append({
                "Fold": i + 1,
                "EV_Score": float(best_score),
                "OOS_Sharpe": metrics["Sharpe Ratio"],
                "OOS_Return": metrics["Total Return"],
                "Signal_Count": total_entries,
            })

            print(
                f"Fold {i+1} | EV Score: {best_score:.3f} | "
                f"Sharpe: {metrics['Sharpe Ratio']} | "
                f"Return: {metrics['Total Return']}"
            )

        return fold_reports, pd.concat(all_returns)