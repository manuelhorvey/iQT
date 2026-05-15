import numpy as np
import pandas as pd


class MultiAssetBacktester:
    def __init__(
        self,
        data_map,
        initial_capital=100000.0,
        risk_manager=None,
        tail_risk_penalty: float = 0.005,
    ):
        self.data_map = data_map
        self.initial_capital = initial_capital
        self.risk_manager = risk_manager
        self.tail_risk_penalty = tail_risk_penalty
        self.portfolio_df = None

    # ---------------------------------------------------
    # core engine
    # ---------------------------------------------------
    def run(self):
        print(f"Running Institutional Backtest | Assets: {len(self.data_map)}")

        returns_df = pd.DataFrame(
            {t: df["Returns"] for t, df in self.data_map.items()}
        ).fillna(0.0)

        hrp = pd.DataFrame(index=returns_df.index, columns=returns_df.columns)

        from allocation import HRPAllocator

        print("Building HRP allocations...")

        for i in range(252, len(returns_df)):
            window = returns_df.iloc[i - 252 : i]

            try:
                allocator = HRPAllocator(window)
                hrp.iloc[i] = allocator.get_weights()
            except Exception:
                hrp.iloc[i] = 1.0 / len(self.data_map)

        # stable initialization
        hrp.iloc[:252] = 1.0 / len(self.data_map)

        # FIX: smooth FIRST, then forward fill
        hrp = hrp.ewm(span=20, adjust=False).mean().ffill()

        asset_pnl = []

        for ticker, df in self.data_map.items():
            specs = self.risk_manager.get_specs(ticker)
            pip_val = self.risk_manager.get_pip_value(ticker)

            df = df.copy()

            # -----------------------------
            # position sizing (stable EV scaling)
            # -----------------------------
            df["Base_Lots"] = (
                self.initial_capital
                * self.risk_manager.risk_per_trade
            ) / (
                df["ATR_14"]
                * self.risk_manager.atr_multiplier
                * specs["lot_size"]
                + 1e-8
            )

            df["Lots"] = (
                df["Base_Lots"] * hrp[ticker].values
            ).clip(lower=0).fillna(0)

            net_pnl = np.zeros(len(df))

            current_pos = 0
            entry_price = 0.0
            sl = tp = 0.0
            lots = 0.0
            bars = 0

            for i in range(1, len(df)):
                row = df.iloc[i]
                prev = df.iloc[i - 1]

                signal = prev.get("Signal", 0)

                # -------------------------
                # EXIT
                # -------------------------
                if current_pos != 0:
                    bars += 1

                    exit_price = row["Close"]
                    hit = False

                    # FX-aware profit in ATR units
                    atr = row["ATR_14"]

                    profit = (
                        (row["High"] - entry_price)
                        if current_pos == 1
                        else (entry_price - row["Low"])
                    )

                    # break-even logic (safe fix)
                    if profit > atr * 1.5:
                        sl = entry_price

                    if current_pos == 1:
                        if row["Low"] < sl:
                            exit_price = sl
                            hit = True
                        elif row["High"] > tp:
                            exit_price = tp
                            hit = True
                        elif signal != 1 or bars > 10:
                            hit = True

                    else:
                        if row["High"] > sl:
                            exit_price = sl
                            hit = True
                        elif row["Low"] < tp:
                            exit_price = tp
                            hit = True
                        elif signal != -1 or bars > 10:
                            hit = True

                    if hit:
                        pnl = (
                            (exit_price - entry_price)
                            * current_pos
                            * lots
                            * specs["lot_size"]
                        )

                        cost = (
                            specs["spread"] * pip_val * specs["lot_size"] * lots
                            + specs["comm"] * lots
                            + 0.5 * pip_val * specs["lot_size"] * lots
                        )

                        net_pnl[i] = pnl - cost

                        current_pos = 0
                        bars = 0

                # -------------------------
                # ENTRY
                # -------------------------
                if current_pos == 0 and signal != 0:
                    current_pos = int(signal)
                    entry_price = row["Open"]
                    lots = df.iloc[i - 1]["Lots"]
                    bars = 0

                    vol = row["ATR_14"]

                    prob = df.iloc[i - 1].get("Signal_Prob", 0.5)
                    regime = df.iloc[i - 1].get("Regime_Label", "Ranging")

                    sl_mult = self.risk_manager.calculate_adaptive_sl_multiplier(
                        prob, regime
                    )
                    rr = self.risk_manager.calculate_dynamic_rr(prob, regime, ticker)

                    sl = entry_price - current_pos * sl_mult * vol
                    tp = entry_price + current_pos * sl_mult * vol * rr

                    cost = (
                        specs["spread"] * pip_val * specs["lot_size"] * lots
                        + specs["comm"] * lots
                    )

                    net_pnl[i] -= cost

                # mark to market already implicit via pnl path

            df["Net_PnL"] = net_pnl
            asset_pnl.append(df["Net_PnL"].rename(ticker))

        portfolio = pd.concat(asset_pnl, axis=1).fillna(0.0)

        self.portfolio_df = pd.DataFrame(index=portfolio.index)

        self.portfolio_df["Daily_PnL"] = portfolio.sum(axis=1)

        # FIX: stochastic tail risk instead of periodic hack
        shock = np.random.binomial(
            1,
            self.tail_risk_penalty,
            size=len(self.portfolio_df),
        ) * self.initial_capital * self.tail_risk_penalty

        self.portfolio_df["Tail_Risk_Cost"] = shock

        self.portfolio_df["Net_Daily_PnL"] = (
            self.portfolio_df["Daily_PnL"] - shock
        )

        returns = self.portfolio_df["Net_Daily_PnL"] / self.initial_capital

        # FIX: equity compounding
        self.portfolio_df["Strategy_Equity"] = (
            self.initial_capital * (1 + returns).cumprod()
        )

        self.portfolio_df["Strategy_Return"] = returns

        return self.portfolio_df

    # ---------------------------------------------------
    # metrics
    # ---------------------------------------------------
    def calculate_metrics(self):
        r = self.portfolio_df["Strategy_Return"].dropna()

        if len(r) == 0:
            return {"Error": "No returns"}

        total_pnl = self.portfolio_df["Net_Daily_PnL"].sum()
        total_return = total_pnl / self.initial_capital

        ann_ret = r.mean() * 252
        ann_vol = r.std() * np.sqrt(252)
        sharpe = ann_ret / ann_vol if ann_vol > 0 else 0

        equity = self.portfolio_df["Strategy_Equity"]
        dd = equity / equity.cummax() - 1

        return {
            "Total PnL": f"${total_pnl:,.2f}",
            "Total Return": f"{total_return:.2%}",
            "Annualized Return": f"{ann_ret:.2%}",
            "Annualized Volatility": f"{ann_vol:.2%}",
            "Sharpe Ratio": f"{sharpe:.2f}",
            "Max Drawdown": f"{dd.min():.2%}",
        }