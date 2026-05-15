import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split
from typing import Dict, List, Optional


class EnsembleModel:
    def __init__(self, params: Optional[Dict] = None) -> None:
        default_params = {
            "n_estimators": 300,
            "learning_rate": 0.02,
            "max_depth": 4,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "reg_lambda": 2.0,
            "random_state": 42,
        }

        if params:
            default_params.update(params)

        self.model = xgb.XGBRegressor(**default_params)

        self.feature_cols = None
        self.accuracy = 0.0

    # ----------------------------
    def _inject_features(self, df: pd.DataFrame) -> pd.DataFrame:
        df_out = df.copy()
        regime = df_out.get("Regime", -1)

        for r in [0, 1, 2]:
            df_out[f"Regime_{r}"] = (regime == r).astype(int)

        return df_out

    # ----------------------------
    def _create_target(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        # Back to honest 1-day prediction to avoid autocorrelation-leakage
        df["Target"] = df["Returns"].shift(-1)
        return df

    # ----------------------------
    def prepare_data(self, df: pd.DataFrame):
        df = self._inject_features(df)
        df = self._create_target(df)

        feature_cols = [
            "RSI_14_Z", "ATR_14_Z", "SMA_Dist_Z",
            "Ret_Lag_1", "Ret_Lag_2",
            "Regime_0", "Regime_1", "Regime_2",
            "ATR_Slope", "DXY_Slope_20",
            "ADX_14", "RSI_7", "BB_Pct", "UUP_Corr_60"
        ]

        available = [c for c in feature_cols if c in df.columns]
        df_clean = df.dropna(subset=available + ["Target"]).copy()

        self.feature_cols = available

        return df_clean[available], df_clean["Target"], df_clean, available

    # ----------------------------
    def prepare_multi_asset_data(self, data_map: Dict[str, pd.DataFrame]):
        Xs, ys = [], []

        for _, df in data_map.items():
            X, y, _, _ = self.prepare_data(df)
            Xs.append(X)
            ys.append(y)

        return (
            pd.concat(Xs).reset_index(drop=True),
            pd.concat(ys).reset_index(drop=True),
            self.feature_cols,
        )

    # ----------------------------
    def train(self, X: pd.DataFrame, y: pd.Series) -> None:
        print("Training EV Regression Model (V7)...")

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, shuffle=False
        )

        self.model.fit(X_train, y_train)
        preds = self.model.predict(X_test)

        self.accuracy = np.mean((preds > 0) == (y_test.values > 0))
        print(f"Directional Alignment: {self.accuracy:.2%}")

        # store distribution for ranking
        self._train_preds = preds

    # ----------------------------
    # V7 SIGNAL ENGINE (RANK-BASED EV)
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
        Generates signals based on rank-transformed EV and cost adjustment.
        Implements Regime Gating to suppress signals in high-entropy/uncertain markets.
        """

        df_out = self._inject_features(df)
        X = df_out[feature_cols]

        raw_ev = self.model.predict(X)

        # ----------------------------
        # RANK TRANSFORM (CORE FIX)
        # Add tiny jitter to prevent identical ranks in low-variance models
        # ----------------------------
        jitter = np.random.normal(0, 1e-9, size=len(raw_ev))
        ranks = pd.Series(raw_ev + jitter).rank(pct=True).values

        # convert rank → centered EV [-1, 1]
        ev = (ranks - 0.5) * 2.0

        # cost adjustment
        ev = ev - cost

        df_out["EV"] = ev

        signals = np.zeros(len(ev))
        position = 0

        # Threshold mapping (e.g. 0.65 -> 0.3)
        entry = threshold * 2 - 1
        exit_level = 0.05

        # Regime Gating: suppress signals if Entropy > Threshold (if gating > 0)
        entropy = df_out.get("Regime_Entropy", pd.Series(0, index=df_out.index))

        for i in range(len(ev)):
            # Apply gating: if entropy is too high, we don't enter new positions
            gated = False
            if regime_gating_threshold > 0 and entropy.iloc[i] > regime_gating_threshold:
                gated = True

            if position == 0:
                if not gated:
                    if ev[i] > entry:
                        position = 1
                    elif ev[i] < -entry:
                        position = -1

            elif position == 1:
                # Exit if EV falls below exit level OR if we become severely gated (optional)
                if ev[i] < exit_level:
                    position = 0

            elif position == -1:
                if ev[i] > -exit_level:
                    position = 0

            signals[i] = position

        df_out["Signal"] = signals

        return df_out

    def get_feature_importance(self):
        return self.model.feature_importances_