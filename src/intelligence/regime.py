import numpy as np
import pandas as pd
from hmmlearn.hmm import GaussianHMM
from sklearn.preprocessing import StandardScaler
from typing import Dict


class RegimeDetector:
    def __init__(self, n_components: int = 3, random_state: int = 42) -> None:
        self.n_components = n_components
        self.random_state = random_state

        self.model = GaussianHMM(
            n_components=n_components,
            covariance_type="full",
            n_iter=2000,
            random_state=random_state,
            init_params="mct",
        )

        self.scaler = StandardScaler()
        self.regime_map: Dict[int, str] = {}

    # ---------------------------------------------------
    # FIT + PREDICT (stable version)
    # ---------------------------------------------------
    def fit_predict(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Fits HMM to returns and volatility to identify market regimes.
        Re-initializes model on each call to ensure fresh fit per asset.
        """
        print("Detecting market regimes using HMM (v2)...")

        # Reset model and scaler state to prevent "overwritten" warnings
        # when reusing this detector for multiple different assets.
        self.model = GaussianHMM(
            n_components=self.n_components,
            covariance_type="full",
            n_iter=2000,
            random_state=self.random_state,
            init_params="mct",
        )
        self.scaler = StandardScaler()

        df_out = df.copy()

        base = df_out[["Returns", "ATR_14"]].dropna()

        if len(base) < 50:
            # fallback safety
            df_out["Regime"] = 0
            df_out["Regime_Confidence"] = 1.0
            df_out["Regime_Label"] = "Unknown"
            return df_out

        scaled = self.scaler.fit_transform(base)

        self.model.fit(scaled)

        regimes = self.model.predict(scaled)
        probs = self.model.predict_proba(scaled)

        # ---------------------------------------------------
        # SAFE ALIGNMENT (fixes your broadcast crash class)
        # ---------------------------------------------------
        idx = base.index

        df_out["Regime"] = np.nan
        df_out["Regime_Confidence"] = np.nan

        df_out.loc[idx, "Regime"] = regimes
        df_out.loc[idx, "Regime_Confidence"] = probs.max(axis=1)

        # full probability state space (EV enhancement)
        for i in range(self.n_components):
            df_out[f"Regime_Prob_{i}"] = np.nan
            df_out.loc[idx, f"Regime_Prob_{i}"] = probs[:, i]

        # ---------------------------------------------------
        # STABLE FORWARD FILL (NO rolling on categorical labels)
        # ---------------------------------------------------
        df_out["Regime"] = df_out["Regime"].ffill().bfill().astype(int)
        df_out["Regime_Confidence"] = df_out["Regime_Confidence"].ffill().bfill()

        # ---------------------------------------------------
        # REGIME STABILITY SIGNAL (NEW v2 FEATURE)
        # ---------------------------------------------------
        prob_cols = [f"Regime_Prob_{i}" for i in range(self.n_components)]
        df_out["Regime_Entropy"] = -np.nansum(
            df_out[prob_cols] * np.log(df_out[prob_cols] + 1e-9),
            axis=1
        )

        # ---------------------------------------------------
        # VOLATILITY-BASED REGIME LABELING (stable + non-leaky)
        # ---------------------------------------------------
        regime_vol = {}

        for r in range(self.n_components):
            mask = df_out["Regime"] == r
            vol = df_out.loc[mask, "ATR_14"].mean()

            regime_vol[r] = vol if not np.isnan(vol) else 1e9

        sorted_states = sorted(regime_vol, key=regime_vol.get)

        # Mapping regimes to Strategy Archetypes
        # Low Vol -> MEAN_REVERSION (Range)
        # High Vol -> TRENDING
        # Medium Vol -> TRANSITION
        self.regime_map = {
            sorted_states[0]: "Low_Vol",
            sorted_states[1]: "Medium_Vol",
            sorted_states[2]: "High_Vol"
        }

        self.archetype_map = {
            sorted_states[0]: "MEAN_REVERSION",
            sorted_states[1]: "TRANSITION",
            sorted_states[2]: "TRENDING"
        }

        # Probabilistic Mapping (V3)
        df_out["P_Range"] = probs[:, sorted_states[0]]
        df_out["P_Transition"] = probs[:, sorted_states[1]]
        df_out["P_Trend"] = probs[:, sorted_states[2]]

        df_out["Regime_Label"] = df_out["Regime"].map(self.regime_map)
        df_out["Regime_Archetype"] = df_out["Regime"].map(self.archetype_map)

        return df_out