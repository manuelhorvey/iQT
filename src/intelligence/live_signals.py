import pandas as pd
import numpy as np
from allocation import HRPAllocator
from typing import Dict, List, Any


class LiveSignalEngine:
    def __init__(self, risk_manager, initial_capital=100000.0):
        self.risk_manager = risk_manager
        self.initial_capital = initial_capital

    # ---------------------------------------------------
    # SAFE SIGNAL GENERATION (NO PRECOMPUTED DEPENDENCY)
    # ---------------------------------------------------
    def _compute_signal(self, ev: float, threshold: float = 0.75):
        if ev > threshold:
            return 1
        elif ev < -threshold:
            return -1
        return 0

    # ---------------------------------------------------
    def generate_tickets(
        self,
        signaled_data,
        model=None,
        feature_cols=None
    ):
        returns_df = pd.DataFrame({
            t: df["Returns"] for t, df in signaled_data.items()
        }).dropna()

        allocator = HRPAllocator(returns_df)
        hrp_weights = allocator.get_weights()

        tickets = []

        for ticker, df in signaled_data.items():
            if len(df) == 0:
                continue

            latest = df.iloc[-1]

            # =================================================
            # V8 FIX: NO DEPENDENCE ON PRECOMPUTED "Signal"
            # =================================================
            ev = float(latest.get("EV", 0.0))

            signal = self._compute_signal(ev)

            if signal == 0:
                continue

            # safety checks
            if not all(k in latest for k in ["Close", "ATR_14", "Regime_Label"]):
                continue

            price = float(latest["Close"])
            atr = float(latest["ATR_14"])

            # EV normalization → pseudo probability (stable mapping)
            prob = 1 / (1 + np.exp(-ev))
            prob = float(np.clip(prob, 0, 1))

            base_lots = self.risk_manager.calculate_lot_size(
                self.initial_capital, price, atr, ticker
            )

            weight = hrp_weights.get(ticker, 1.0 / max(len(hrp_weights), 1))
            final_lots = round(base_lots * weight, 2)

            sl_mult = self.risk_manager.calculate_adaptive_sl_multiplier(
                prob, latest["Regime_Label"]
            )

            rr = self.risk_manager.calculate_dynamic_rr(
                prob, latest["Regime_Label"], ticker
            )

            sl_distance = atr * sl_mult
            pip_val = self.risk_manager.get_pip_value(ticker)

            stop_loss = price - sl_distance if signal == 1 else price + sl_distance
            take_profit = (
                price + (sl_distance * rr)
                if signal == 1
                else price - (sl_distance * rr)
            )

            conviction = "STRONG" if prob > 0.7 or prob < 0.3 else "MODERATE"

            tickets.append({
                "ticker": ticker,
                "regime": latest["Regime_Label"],
                "signal": "BUY" if signal == 1 else "SELL",
                "conviction": conviction,
                "confidence": f"{prob * 100:.1f}%",
                "price": price,
                "lots": final_lots,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "sl_pips": round(sl_distance / pip_val, 1),
                "risk_reward": f"1:{rr}",
                "hrp_scale": f"{weight * 100:.0f}%"
            })

        return tickets

    # ---------------------------------------------------
    def get_portfolio_summary(self, tickets, signaled_data):
        total_lots = sum(t["lots"] for t in tickets)

        vol_list = []
        for df in signaled_data.values():
            if "Returns" in df:
                vol_list.append(df["Returns"].std() * np.sqrt(252))

        avg_vol = np.mean(vol_list) if vol_list else 0.0

        return {
            "active_signals": len(tickets),
            "total_exposure_lots": round(total_lots, 2),
            "portfolio_vol": f"{avg_vol * 100:.2f}%",
            "max_risk_per_trade": f"{self.risk_manager.risk_per_trade * 100:.1f}%",
            "highest_conviction": tickets[0]["ticker"] if tickets else None
        }