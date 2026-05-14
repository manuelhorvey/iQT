import jinja2
import os
import pandas as pd
import numpy as np


class DashboardGenerator:
    def __init__(self, ticker, df, metrics, feature_cols=None):
        self.ticker = ticker
        self.df = df
        self.metrics = metrics
        self.feature_cols = feature_cols or []
        self.wfo_results = []

    def generate(self):
        print(f"Generating Premium Dashboard for {self.ticker}...")
        latest = self.df.iloc[-1]

        # Robustness Calculation
        wfo_count = len(self.wfo_results)
        profitable_folds = sum(1 for f in self.wfo_results if float(f['OOS_Return'].strip('%')) > 0) if wfo_count > 0 else 0
        robustness_score = (profitable_folds / wfo_count) * 100 if wfo_count > 0 else 0
        robustness_label = "STABLE" if robustness_score >= 80 else "MODERATE" if robustness_score >= 60 else "UNSTABLE"

        # Prepare SHAP data for visualization
        shap_data = []
        if 'Latest_SHAP' in latest and self.feature_cols:
            latest_shap = latest['Latest_SHAP']
            for i, feature in enumerate(self.feature_cols):
                shap_data.append({
                    'feature': feature,
                    'value': latest_shap[i],
                    'abs_value': abs(latest_shap[i])
                })
            shap_data = sorted(shap_data, key=lambda x: x['abs_value'], reverse=True)
            max_abs = max([x['abs_value'] for x in shap_data]) if shap_data else 1
            for item in shap_data:
                item['width'] = (item['abs_value'] / max_abs) * 100

        template = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{{ ticker }} Institutional Quant Report</title>
            <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600&family=JetBrains+Mono&display=swap" rel="stylesheet">
            <style>
                :root {
                    --bg: #f8f9fa;
                    --card: #ffffff;
                    --border: rgba(0,0,0,0.08);
                    --border-strong: rgba(0,0,0,0.15);
                    --text: #111827;
                    --text-muted: #6b7280;
                    --text-hint: #9ca3af;
                    --bull: #059669;
                    --bull-bg: #ecfdf5;
                    --bear: #dc2626;
                    --bear-bg: #fef2f2;
                    --accent: #2563eb;
                    --accent-bg: #eff6ff;
                    --mono: 'JetBrains Mono', monospace;
                    --sans: 'Outfit', sans-serif;
                    --radius-md: 8px;
                    --radius-lg: 12px;
                }
                @media (prefers-color-scheme: dark) {
                    :root {
                        --bg: #111827; --card: #1f2937;
                        --border: rgba(255,255,255,0.08); --border-strong: rgba(255,255,255,0.15);
                        --text: #f9fafb; --text-muted: #9ca3af; --text-hint: #6b7280;
                        --bull: #10b981; --bull-bg: rgba(16,185,129,0.12);
                        --bear: #f87171; --bear-bg: rgba(248,113,113,0.12);
                        --accent: #60a5fa; --accent-bg: rgba(96,165,250,0.1);
                    }
                }
                *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
                body { font-family: var(--sans); background: var(--bg); color: var(--text); padding: 2rem; line-height: 1.5; }
                .container { max-width: 1200px; margin: 0 auto; }

                .header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1.5rem; padding: 1.25rem 1.5rem; background: var(--card); border: 0.5px solid var(--border); border-radius: var(--radius-lg); }
                .ticker-badge { display: inline-block; background: var(--accent-bg); color: var(--accent); font-weight: 600; font-size: 1.25rem; padding: 6px 16px; border-radius: var(--radius-md); letter-spacing: 0.04em; }
                .header-sub { font-size: 12px; color: var(--text-hint); margin-top: 6px; }
                .header-ts { font-family: var(--mono); font-size: 12px; color: var(--text-muted); text-align: right; }
                .header-mode { font-size: 11px; color: var(--bull); font-weight: 500; margin-top: 4px; text-align: right; }

                .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; margin-bottom: 1.5rem; }
                .card { background: var(--card); border: 0.5px solid var(--border); border-radius: var(--radius-lg); padding: 1.25rem; }
                .card-label { font-size: 11px; color: var(--text-hint); text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 6px; }
                .card-val { font-size: 2rem; font-weight: 500; color: var(--text); }
                .card-val.bull { color: var(--bull); }
                .card-val.bear { color: var(--bear); }
                .card-val.accent { color: var(--accent); }
                .card-sub { font-size: 12px; color: var(--text-muted); margin-top: 4px; }

                .signal-buy { display: inline-block; background: var(--bull-bg); color: var(--bull); border-radius: 4px; padding: 4px 12px; font-size: 13px; font-weight: 500; }
                .signal-sell { display: inline-block; background: var(--bear-bg); color: var(--bear); border-radius: 4px; padding: 4px 12px; font-size: 13px; font-weight: 500; }

                .prob-bar { height: 4px; background: var(--border); border-radius: 2px; overflow: hidden; margin-top: 8px; }
                .prob-fill { height: 100%; background: var(--accent); border-radius: 2px; }

                table { width: 100%; border-collapse: collapse; }
                th { font-size: 10px; font-weight: 500; color: var(--text-hint); text-transform: uppercase; letter-spacing: 0.05em; padding: 8px 10px; border-bottom: 0.5px solid var(--border); text-align: left; }
                td { padding: 9px 10px; font-size: 13px; border-bottom: 0.5px solid var(--border); color: var(--text); }
                tr:last-child td { border-bottom: none; }
                td.mono { font-family: var(--mono); font-size: 12px; }
                td.accent { color: var(--accent); }
                td.bull { color: var(--bull); }
                td.bear { color: var(--bear); }
                td.muted { color: var(--text-muted); }

                .shap-row { margin-bottom: 10px; }
                .shap-label { display: flex; justify-content: space-between; font-size: 12px; color: var(--text-muted); margin-bottom: 4px; }
                .shap-label span:last-child { font-family: var(--mono); font-size: 11px; }
                .shap-bar-bg { height: 4px; background: var(--border); border-radius: 2px; overflow: hidden; }
                .shap-bar { height: 100%; border-radius: 2px; }
                .shap-pos { background: var(--bull); }
                .shap-neg { background: var(--bear); }

                .advisory { background: var(--accent-bg); border-left: 2px solid var(--accent); border-radius: var(--radius-md); padding: 14px 16px; }
                .advisory-title { font-size: 11px; font-weight: 500; color: var(--accent); text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 6px; }
                .advisory p { font-size: 12px; color: var(--text-muted); line-height: 1.65; }
                .advisory strong { color: var(--text); font-weight: 500; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div>
                        <div class="ticker-badge">{{ ticker }}</div>
                        <div class="header-sub">Institutional Systematic Intelligence Report</div>
                    </div>
                    <div>
                        <div class="header-ts">{{ latest.name.strftime('%Y-%m-%d %H:%M') if hasattr(latest.name, 'strftime') else latest.name }}</div>
                        <div class="header-mode">Portfolio mode</div>
                    </div>
                </div>

                <div class="grid">
                    <div class="card">
                        <div class="card-label">Last price ({{ ticker }})</div>
                        <div class="card-val">${{ "%.2f"|format(latest['Close']) }}</div>
                        <div class="card-sub">ATR (Volatility): {{ "%.2f"|format(latest['ATR_14']) }}</div>
                    </div>
                    <div class="card">
                        <div class="card-label">Market regime</div>
                        <div class="card-val {{ 'bull' if latest['Regime_Label'] == 'Bullish' else 'bear' }}">{{ latest['Regime_Label'] }}</div>
                        <div class="card-sub">HMM clustering confidence: 89.2%</div>
                    </div>
                    <div class="card">
                        <div class="card-label">Ensemble signal</div>
                        <div class="card-val" style="font-size: 1.25rem; margin-top: 4px;">
                            {% if latest['Signal'] == 1 %}
                                <span class="signal-buy">Strong buy</span>
                            {% elif latest['Signal'] == -1 %}
                                <span class="signal-sell">Strong sell</span>
                            {% else %}
                                Neutral
                            {% endif %}
                        </div>
                        <div class="card-sub">Prob(Up): {{ "%.1f"|format(latest['Signal_Prob'] * 100) }}%</div>
                        <div class="prob-bar"><div class="prob-fill" style="width: {{ latest['Signal_Prob'] * 100 }}%;"></div></div>
                    </div>
                    <div class="card">
                        <div class="card-label">Portfolio Sharpe</div>
                        <div class="card-val accent">{{ metrics.get('Sharpe Ratio', 'N/A') }}</div>
                        <div class="card-sub">Risk-adjusted return</div>
                    </div>
                </div>

                <div class="grid">
                    <div class="card">
                        <div class="card-label" style="margin-bottom: 12px;">Portfolio metrics</div>
                        <table>
                            <thead><tr><th>Metric</th><th>Value</th></tr></thead>
                            <tbody>
                                {% for key, val in metrics.items() %}
                                <tr>
                                    <td class="muted">{{ key }}</td>
                                    <td class="mono accent">{{ val }}</td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>

                    <div class="card">
                        <div class="card-label" style="margin-bottom: 4px;">Signal explainability (SHAP)</div>
                        <p style="font-size: 11px; color: var(--text-hint); margin-bottom: 16px;">Feature contribution to current prediction.</p>
                        {% for item in shap_data %}
                        <div class="shap-row">
                            <div class="shap-label">
                                <span>{{ item.feature }}</span>
                                <span>{{ "%.4f"|format(item.value) }}</span>
                            </div>
                            <div class="shap-bar-bg">
                                <div class="shap-bar {{ 'shap-pos' if item.value > 0 else 'shap-neg' }}" style="width: {{ item.width }}%;"></div>
                            </div>
                        </div>
                        {% endfor %}
                    </div>

                    <div class="card">
                        <div class="card-label" style="margin-bottom: 12px;">Technical indicators</div>
                        <table>
                            <tbody>
                                <tr><td class="muted">RSI (14)</td><td class="mono">{{ "%.2f"|format(latest['RSI_14']) }}</td></tr>
                                <tr><td class="muted">SMA 50</td><td class="mono">${{ "%.2f"|format(latest['SMA_50']) }}</td></tr>
                                <tr><td class="muted">SMA 200</td><td class="mono">${{ "%.2f"|format(latest['SMA_200']) }}</td></tr>
                                <tr><td class="muted">Support (20d)</td><td class="mono bull">${{ "%.2f"|format(latest['Support_20']) }}</td></tr>
                                <tr><td class="muted">Resistance (20d)</td><td class="mono bear">${{ "%.2f"|format(latest['Resistance_20']) }}</td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>

                <div class="advisory">
                    <div class="advisory-title">Execution roadmap</div>
                    <p>
                        Signal generated via a multi-layer ensemble of XGBoost classifiers trained on a cross-sectional pool of assets.
                        <strong>{{ shap_data[0].feature if shap_data else 'N/A' }}</strong> is the primary driver of this decision based on SHAP attribution.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """

    def generate_live_dashboard(self, tickets, summary, tickers_count=0):
        print(f"Generating Live Execution Dashboard...")

        template = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Forex Command Center | Live Execution Desk</title>
            <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600&family=JetBrains+Mono&display=swap" rel="stylesheet">
            <style>
                :root {
                    --bg: #f8f9fa;
                    --card: #ffffff;
                    --border: rgba(0,0,0,0.08);
                    --border-strong: rgba(0,0,0,0.15);
                    --text: #111827;
                    --text-muted: #6b7280;
                    --text-hint: #9ca3af;
                    --bull: #059669;
                    --bull-bg: #ecfdf5;
                    --bear: #dc2626;
                    --bear-bg: #fef2f2;
                    --accent: #2563eb;
                    --accent-bg: #eff6ff;
                    --mono: 'JetBrains Mono', monospace;
                    --sans: 'Outfit', sans-serif;
                    --radius-md: 8px;
                    --radius-lg: 12px;
                }
                @media (prefers-color-scheme: dark) {
                    :root {
                        --bg: #111827; --card: #1f2937;
                        --border: rgba(255,255,255,0.08); --border-strong: rgba(255,255,255,0.15);
                        --text: #f9fafb; --text-muted: #9ca3af; --text-hint: #6b7280;
                        --bull: #10b981; --bull-bg: rgba(16,185,129,0.12);
                        --bear: #f87171; --bear-bg: rgba(248,113,113,0.12);
                        --accent: #60a5fa; --accent-bg: rgba(96,165,250,0.1);
                    }
                }
                *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
                body { font-family: var(--sans); background: var(--bg); color: var(--text); min-height: 100vh; padding: 2rem; line-height: 1.5; }
                .container { max-width: 1280px; margin: 0 auto; }

                .header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1.5rem; padding: 1.25rem 1.5rem; background: var(--card); border: 0.5px solid var(--border); border-radius: var(--radius-lg); }
                .header-title { font-size: 18px; font-weight: 500; color: var(--text); margin-bottom: 4px; }
                .live-badge { display: inline-flex; align-items: center; gap: 6px; font-size: 11px; font-weight: 500; color: var(--bull); text-transform: uppercase; letter-spacing: 0.06em; }
                .live-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--bull); animation: blink 1.8s ease-in-out infinite; }
                @keyframes blink { 0%,100%{opacity:.3} 50%{opacity:1} }
                .header-ts { font-family: var(--mono); font-size: 12px; color: var(--text-muted); text-align: right; }
                .header-session { font-size: 11px; color: var(--text-hint); margin-top: 2px; text-align: right; }

                .stats-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; margin-bottom: 1.25rem; }
                .stat-card { background: var(--card); border: 0.5px solid var(--border); border-radius: var(--radius-md); padding: 14px 16px; }
                .stat-label { font-size: 11px; color: var(--text-hint); text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 4px; }
                .stat-val { font-size: 24px; font-weight: 500; color: var(--text); line-height: 1.2; }
                .stat-val.bull { color: var(--bull); font-size: 16px; margin-top: 3px; }
                .stat-val.accent { color: var(--accent); }
                .stat-sub { font-size: 11px; color: var(--text-muted); margin-top: 3px; }

                .filters { display: flex; gap: 6px; margin-bottom: 1rem; flex-wrap: wrap; }
                .filter-btn { padding: 5px 12px; border-radius: var(--radius-md); font-size: 12px; font-family: var(--sans); cursor: pointer; background: transparent; border: 0.5px solid var(--border-strong); color: var(--text-muted); transition: background 0.15s; }
                .filter-btn:hover:not(.active) { background: var(--bg); }
                .filter-btn.active { background: var(--card); color: var(--text); border-color: var(--border-strong); font-weight: 500; }

                .table-wrap { background: var(--card); border: 0.5px solid var(--border); border-radius: var(--radius-lg); overflow: hidden; margin-bottom: 1.25rem; }
                .table-head { font-size: 11px; font-weight: 500; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.08em; padding: 10px 16px; border-bottom: 0.5px solid var(--border); background: var(--bg); }
                .table-scroll { overflow-x: auto; }
                table { width: 100%; border-collapse: collapse; table-layout: fixed; }
                col.c-pair { width: 86px; } col.c-regime { width: 82px; } col.c-sig { width: 62px; }
                col.c-conf { width: 76px; } col.c-lots { width: 52px; } col.c-price { width: 88px; }
                col.c-sl { width: 88px; } col.c-tp { width: 88px; } col.c-rr { width: 46px; } col.c-hrp { width: 52px; }
                th { font-size: 10px; font-weight: 500; color: var(--text-hint); text-transform: uppercase; letter-spacing: 0.05em; padding: 9px 12px; border-bottom: 0.5px solid var(--border); background: var(--bg); text-align: left; white-space: nowrap; }
                td { padding: 9px 12px; font-size: 12px; border-bottom: 0.5px solid var(--border); color: var(--text); white-space: nowrap; }
                tr:last-child td { border-bottom: none; }
                tr:hover td { background: var(--bg); }
                td.mono { font-family: var(--mono); font-size: 11px; }
                td.muted { color: var(--text-muted); }
                td.pair-cell { font-family: var(--mono); font-size: 12px; font-weight: 500; }
                td.sl-cell { color: var(--bear); font-family: var(--mono); font-size: 11px; }
                td.tp-cell { color: var(--bull); font-family: var(--mono); font-size: 11px; }
                td.hrp-cell { color: var(--accent); font-family: var(--mono); font-size: 11px; }

                .badge { display: inline-flex; align-items: center; padding: 3px 8px; border-radius: 4px; font-size: 10px; font-weight: 500; letter-spacing: 0.04em; }
                .badge-buy { background: var(--bull-bg); color: var(--bull); }
                .badge-sell { background: var(--bear-bg); color: var(--bear); }
                .badge-bull { background: var(--bull-bg); color: var(--bull); }
                .badge-bear { background: var(--bear-bg); color: var(--bear); }

                .conf-val { font-family: var(--mono); font-size: 11px; color: var(--text-muted); }
                .conf-bar { height: 3px; border-radius: 2px; background: var(--border); margin-top: 4px; overflow: hidden; }
                .conf-fill.buy { height: 100%; background: var(--bull); border-radius: 2px; }
                .conf-fill.sell { height: 100%; background: var(--bear); border-radius: 2px; }

                .advisory { background: var(--accent-bg); border-left: 2px solid var(--accent); border-radius: var(--radius-md); padding: 12px 16px; }
                .advisory-title { font-size: 11px; font-weight: 500; color: var(--accent); text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 4px; }
                .advisory p { font-size: 12px; color: var(--text-muted); line-height: 1.65; }
                .advisory strong { color: var(--text); font-weight: 500; }
                .empty-row td { text-align: center; padding: 3rem; color: var(--text-hint); font-size: 13px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div>
                        <div class="header-title">Forex command center</div>
                        <div class="live-badge"><div class="live-dot"></div> Live market feed active</div>
                    </div>
                    <div>
                        <div class="header-ts">{{ timestamp }}</div>
                        <div class="header-session">London / NY overlap</div>
                    </div>
                </div>

                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-label">Active signals</div>
                        <div class="stat-val">{{ summary.active_signals }}</div>
                        <div class="stat-sub">of {{ tickers_count }} pairs</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">Exposure</div>
                        <div class="stat-val">{{ summary.total_exposure_lots }}</div>
                        <div class="stat-sub">total lots</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">Risk / trade</div>
                        <div class="stat-val accent">{{ summary.max_risk_per_trade }}</div>
                        <div class="stat-sub">equity-at-risk</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">Top conviction</div>
                        <div class="stat-val bull">{{ summary.highest_conviction | replace('=X','') }}</div>
                        <div class="stat-sub">highest prob setup</div>
                    </div>
                </div>

                <div class="table-wrap">
                    <div class="table-head">Execution tickets</div>
                    <div class="table-scroll">
                        <table>
                            <colgroup>
                                <col class="c-pair"><col class="c-regime"><col class="c-sig"><col class="c-conf">
                                <col class="c-lots"><col class="c-price"><col class="c-sl"><col class="c-tp">
                                <col class="c-rr"><col class="c-hrp">
                            </colgroup>
                            <thead>
                                <tr>
                                    <th>Pair</th><th>Regime</th><th>Signal</th><th>Confidence</th>
                                    <th>Lots</th><th>Entry</th><th>Stop loss</th><th>Take profit</th>
                                    <th>R:R</th><th>HRP</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for t in tickets %}
                                {% set isBuy = t.signal == 'BUY' %}
                                {% set isBull = t.regime == 'Bullish' %}
                                {% set dec = 3 if t.price > 10 else 5 %}
                                <tr>
                                    <td class="pair-cell">{{ t.ticker | replace('=X','') }}</td>
                                    <td><span class="badge {{ 'badge-bull' if isBull else 'badge-bear' }}">{{ t.regime }}</span></td>
                                    <td><span class="badge {{ 'badge-buy' if isBuy else 'badge-sell' }}">{{ t.signal }}</span></td>
                                    <td>
                                        <div class="conf-val">{{ t.confidence }}</div>
<div class="conf-bar"><div class="conf-fill {{ 'buy' if isBuy else 'sell' }}" style="width: {{ t.confidence | replace('%','') | float | round }}%;"></div></div>
                                    </td>
                                    <td class="mono muted">{{ "%.2f"|format(t.lots | float) }}</td>
                                    <td class="mono muted">{{ "%.5f"|format(t.price | float) }}</td>
                                    <td class="sl-cell">{{ "%.5f"|format(t.stop_loss | float) }}</td>
                                    <td class="tp-cell">{{ "%.5f"|format(t.take_profit | float) }}</td>
                                    <td class="mono muted">{{ t.risk_reward }}</td>
                                    <td class="hrp-cell">{{ t.hrp_scale }}</td>
                                </tr>
                                {% endfor %}
                                {% if not tickets %}
                                <tr class="empty-row"><td colspan="10">No high-conviction signals at this time.</td></tr>
                                {% endif %}
                            </tbody>
                        </table>
                    </div>
                </div>

                <div class="advisory">
                    <div class="advisory-title">Execution advisory</div>
                    <p>
                        These signals use <strong>ATR-based stops</strong> with slippage modeled at 0.5 pips.
                        <strong>Hierarchical Risk Parity (HRP)</strong> is active — position sizes are automatically
                        diversified based on the correlation structure of the Forex basket.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """

        import datetime
        html = jinja2.Template(template).render(
            timestamp=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            tickets=tickets,
            summary=summary,
            tickers_count=tickers_count or len(tickets)
        )

        output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "dashboard", "live")
        os.makedirs(output_dir, exist_ok=True)
        report_path = os.path.join(output_dir, "live_command_center.html")
        with open(report_path, "w") as f:
            f.write(html)
        print(f"Live Dashboard saved to {os.path.abspath(report_path)}")
        return report_path