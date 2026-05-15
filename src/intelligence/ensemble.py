import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split
from typing import Dict, List, Optional


class EnsembleModel:
    def __init__(self, params: Optional[Dict] = None) -> None:
        default_params = {
            "n_estimators": 250,
            "learning_rate": 0.02,
            "max_depth": 3,
            "subsample": 0.7,
            "colsample_bytree": 0.7,
            "reg_lambda": 3.0,
            "random_state": 42,
        }

        if params:
            default_params.update(params)

        # Dual Experts
        self.trend_expert = xgb.XGBRegressor(**default_params)
        self.range_expert = xgb.XGBRegressor(**default_params)
        
        # Meta-label filter (Target: Will the primary signal be profitable?)
        self.meta_filter = xgb.XGBClassifier(
            n_estimators=100, max_depth=3, learning_rate=0.05, random_state=42
        )

        self.feature_cols = None
        
        # Explicit Feature Sets
        self.trend_features = [
            "SMA_Dist_Z", "Ret_Lag_1", "ATR_Slope", "ADX_14", "DXY_Slope_20", "UUP_Corr_60"
        ]
        self.range_features = [
            "RSI_14_Z", "RSI_7", "BB_Pct", "Price_ZScore_20", "BB_Dist_High", "BB_Dist_Low"
        ]
        self.accuracy = 0.0

    # ----------------------------
    def _inject_features(self, df: pd.DataFrame) -> pd.DataFrame:
        df_out = df.copy()
        return df_out

    # ----------------------------
    def _create_target(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["Target"] = df["Returns"].shift(-1)
        return df

    # ----------------------------
    def prepare_data(self, df: pd.DataFrame):
        df = self._inject_features(df)
        df = self._create_target(df)

        feature_cols = sorted(list(set(self.trend_features + self.range_features)))

        available = [c for c in feature_cols if c in df.columns]
        df_clean = df.dropna(subset=available + ["Target"]).copy()

        self.feature_cols = available

        return df_clean[available], df_clean["Target"], df_clean, available

    # ----------------------------
    def prepare_multi_asset_data(self, data_map: Dict[str, pd.DataFrame]):
        Xs, ys, dfs = [], [], []

        for _, df in data_map.items():
            X, y, df_full, _ = self.prepare_data(df)
            Xs.append(X)
            ys.append(y)
            dfs.append(df_full)

        return (
            pd.concat(Xs).reset_index(drop=True),
            pd.concat(ys).reset_index(drop=True),
            pd.concat(dfs).reset_index(drop=True),
            self.feature_cols,
        )

    # ----------------------------
    def train(self, X: pd.DataFrame, y: pd.Series, df_full: pd.DataFrame = None) -> None:
        """
        Trains the Experts using Probabilistic weighting.
        """
        print("Training RG-MoE Specialists (Trend + Range)...")

        if df_full is None:
            self.trend_expert.fit(X[self.trend_features], y)
            self.range_expert.fit(X[self.range_features], y)
            return

        # 1. Train Trend Expert with probabilistic weight
        p_trend = df_full["P_Trend"].values
        self.trend_expert.fit(X[self.trend_features], y, sample_weight=p_trend)
        print(f"  - Trend Expert trained on weighted samples (Avg P: {np.mean(p_trend):.2f})")

        # 2. Train Range Expert with probabilistic weight
        p_range = df_full["P_Range"].values
        self.range_expert.fit(X[self.range_features], y, sample_weight=p_range)
        print(f"  - Range Expert trained on weighted samples (Avg P: {np.mean(p_range):.2f})")

        # Meta-accuracy check
        preds = self.model_predict(X, df_full)
        self.accuracy = np.mean((preds > 0) == (y.values > 0))
        print(f"MoE Directional Alignment: {self.accuracy:.2%}")

    def model_predict(self, X: pd.DataFrame, df: pd.DataFrame) -> np.ndarray:
        """
        Blends expert predictions using HMM probabilities (Soft Activation).
        """
        # Get raw predictions from each expert using their specific feature set
        p_trend_val = self.trend_expert.predict(X[self.trend_features])
        p_range_val = self.range_expert.predict(X[self.range_features])
        
        # Get regime probabilities
        w_trend = df["P_Trend"].values
        w_range = df["P_Range"].values
        w_transition = df["P_Transition"].values
        
        # Unified blending
        # In transition zones, we take a conservative blend of both
        final_preds = (w_trend * p_trend_val) + (w_range * p_range_val) + (w_transition * (p_trend_val + p_range_val) / 2.0)
                
        return final_preds

    # ----------------------------
    # V9 SIGNAL ENGINE (PROBABILISTIC MoE + ANTI-CONFLICT)
    # ----------------------------
    def generate_signals(
        self,
        df: pd.DataFrame,
        feature_cols: List[str],
        cost: float = 0.0001,
        threshold: float = 0.65,
        regime_gating_threshold: float = 0.0,
    ) -> pd.DataFrame:
        """
        Generates signals using Soft MoE Activation and Anti-Conflict logic.
        """

        df_out = self._inject_features(df)
        X = df_out[self.feature_cols]

        # Expert predictions for conflict check
        ev_trend = self.trend_expert.predict(X[self.trend_features])
        ev_range = self.range_expert.predict(X[self.range_features])

        # Blended EV
        raw_ev = self.model_predict(X, df_out)

        # ----------------------------
        # RANK TRANSFORM (CORE FIX)
        # ----------------------------
        jitter = np.random.normal(0, 1e-9, size=len(raw_ev))
        ranks = pd.Series(raw_ev + jitter).rank(pct=True).values
        ev = (ranks - 0.5) * 2.0
        ev = ev - cost

        df_out["EV"] = ev

        signals = np.zeros(len(ev))
        position = 0

        # Threshold mapping (e.g. 0.65 -> 0.3)
        # Safety: Normalize if percentage (e.g. 65 -> 0.65)
        if threshold > 1.0:
            threshold = threshold / 100.0

        entry = threshold * 2 - 1
        exit_level = 0.05

        # Regime Gating
        entropy = df_out.get("Regime_Entropy", pd.Series(0, index=df_out.index))

        for i in range(len(ev)):
            gated = False
            if regime_gating_threshold > 0 and entropy.iloc[i] > regime_gating_threshold:
                gated = True

            # ANTI-CONFLICT RULE: Only veto on violent disagreement
            conflict = False
            if np.sign(ev_trend[i]) != np.sign(ev_range[i]):
                if abs(ev_trend[i]) > 0.005 and abs(ev_range[i]) > 0.005:
                    conflict = True

            if position == 0:
                if not gated and not conflict:
                    if ev[i] > entry:
                        position = 1
                    elif ev[i] < -entry:
                        position = -1

            elif position == 1:
                # Exit if EV falls below exit level
                if ev[i] < exit_level:
                    position = 0

            elif position == -1:
                if ev[i] > -exit_level:
                    position = 0

            signals[i] = position

        df_out["Signal"] = signals

        return df_out

    def get_feature_importance(self):
        # Weighted average feature importance or return dict
        return self.trend_expert.feature_importances_
