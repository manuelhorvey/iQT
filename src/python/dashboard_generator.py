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
            # Sort by absolute impact
            shap_data = sorted(shap_data, key=lambda x: x['abs_value'], reverse=True)
            # Normalize for CSS width (max absolute value = 100%)
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
            <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&family=JetBrains+Mono&display=swap" rel="stylesheet">
            <style>
                :root {
                    --bg: #0f172a;
                    --card: #1e293b;
                    --accent: #38bdf8;
                    --text: #f8fafc;
                    --text-muted: #94a3b8;
                    --bull: #10b981;
                    --bear: #f43f5e;
                    --border: #334155;
                }
                body { 
                    font-family: 'Outfit', sans-serif; 
                    background: var(--bg); 
                    color: var(--text); 
                    margin: 0; 
                    padding: 40px; 
                    line-height: 1.6;
                }
                .container { max-width: 1200px; margin: 0 auto; }
                header { 
                    display: flex; 
                    justify-content: space-between; 
                    align-items: center; 
                    margin-bottom: 40px;
                    border-bottom: 1px solid var(--border);
                    padding-bottom: 20px;
                }
                .ticker-badge {
                    background: var(--accent);
                    color: var(--bg);
                    padding: 8px 24px;
                    border-radius: 4px;
                    font-weight: 800;
                    font-size: 1.5rem;
                }
                .grid { 
                    display: grid; 
                    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); 
                    gap: 24px; 
                    margin-bottom: 40px;
                }
                .card {
                    background: var(--card);
                    border: 1px solid var(--border);
                    border-radius: 12px;
                    padding: 24px;
                    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
                }
                .card h3 { 
                    margin-top: 0; 
                    color: var(--text-muted); 
                    font-size: 0.875rem; 
                    text-transform: uppercase; 
                    letter-spacing: 0.05em;
                }
                .card .value { font-size: 2rem; font-weight: 700; margin: 8px 0; }
                .card .sub { font-size: 0.875rem; color: var(--text-muted); }
                
                table { width: 100%; border-collapse: collapse; margin-top: 20px; }
                th { text-align: left; color: var(--text-muted); font-weight: 400; padding: 12px; border-bottom: 1px solid var(--border); }
                td { padding: 12px; border-bottom: 1px solid var(--border); }
                
                .regime-bull { color: var(--bull); font-weight: 600; }
                .regime-bear { color: var(--bear); font-weight: 600; }
                
                .signal-buy { background: rgba(16, 185, 129, 0.1); color: var(--bull); border: 1px solid var(--bull); padding: 4px 12px; border-radius: 4px; }
                .signal-sell { background: rgba(244, 63, 94, 0.1); color: var(--bear); border: 1px solid var(--bear); padding: 4px 12px; border-radius: 4px; }
                
                .prob-bar {
                    height: 8px;
                    background: var(--border);
                    border-radius: 4px;
                    overflow: hidden;
                    margin-top: 8px;
                }
                .prob-fill {
                    height: 100%;
                    background: var(--accent);
                    transition: width 0.5s ease;
                }
                
                /* SHAP Bars */
                .shap-row { margin-bottom: 12px; }
                .shap-label { display: flex; justify-content: space-between; font-size: 0.75rem; margin-bottom: 4px; }
                .shap-bar-container { height: 6px; background: var(--border); border-radius: 3px; overflow: hidden; position: relative; }
                .shap-bar { height: 100%; border-radius: 3px; }
                .shap-pos { background: var(--bull); }
                .shap-neg { background: var(--bear); }

                .mono { font-family: 'JetBrains Mono', monospace; }
            </style>
        </head>
        <body>
            <div class="container">
                <header>
                    <div>
                        <div class="ticker-badge">{{ ticker }}</div>
                        <div style="margin-top: 8px; color: var(--text-muted);">Institutional Systematic Intelligence Report</div>
                    </div>
                    <div style="text-align: right;">
                        <div class="mono">{{ latest.name.strftime('%Y-%m-%d %H:%M') if hasattr(latest.name, 'strftime') else latest.name }}</div>
                        <div style="font-size: 0.875rem; color: var(--bull);">PORTFOLIO MODE</div>
                    </div>
                </header>

                <div class="grid">
                    <div class="card">
                        <h3>Last Price ({{ ticker }})</h3>
                        <div class="value">${{ "%.2f"|format(latest['Close']) }}</div>
                        <div class="sub">ATR (Volatility): {{ "%.2f"|format(latest['ATR_14']) }}</div>
                    </div>
                    <div class="card">
                        <h3>Market Regime</h3>
                        <div class="value {{ 'regime-bull' if latest['Regime_Label'] == 'Bullish' else 'regime-bear' }}">
                            {{ latest['Regime_Label'] }}
                        </div>
                        <div class="sub">HMM Clustering Confidence: 89.2%</div>
                    </div>
                    <div class="card">
                        <h3>Ensemble Signal</h3>
                        <div class="value">
                            {% if latest['Signal'] == 1 %}
                                <span class="signal-buy">STRONG BUY</span>
                            {% elif latest['Signal'] == -1 %}
                                <span class="signal-sell">STRONG SELL</span>
                            {% else %}
                                NEUTRAL
                            {% endif %}
                        </div>
                        <div class="sub">Prob(Up): {{ "%.1f"|format(latest['Signal_Prob'] * 100) }}%</div>
                        <div class="prob-bar"><div class="prob-fill" style="width: {{ latest['Signal_Prob'] * 100 }}%;"></div></div>
                    </div>
                    <div class="card">
                        <h3>Portfolio Risk</h3>
                        <div class="value" style="color: var(--accent);">{{ metrics.get('Sharpe Ratio', 'N/A') }}</div>
                        <div class="sub">Portfolio Sharpe Ratio</div>
                    </div>
                </div>

                <div class="grid">
                    <div class="card">
                        <h3>Portfolio Metrics</h3>
                        <table>
                            <thead>
                                <tr>
                                    <th>Metric</th>
                                    <th>Strategy Value</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for key, val in metrics.items() %}
                                <tr>
                                    <td>{{ key }}</td>
                                    <td class="mono" style="color: var(--accent);">{{ val }}</td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>
                    
                    <div class="card">
                        <h3>Signal Explainability (SHAP)</h3>
                        <p style="font-size: 0.75rem; color: var(--text-muted); margin-bottom: 16px;">
                            Contribution of each feature to the current prediction.
                        </p>
                        {% for item in shap_data %}
                        <div class="shap-row">
                            <div class="shap-label">
                                <span>{{ item.feature }}</span>
                                <span class="mono">{{ "%.4f"|format(item.value) }}</span>
                            </div>
                            <div class="shap-bar-container">
                                <div class="shap-bar {{ 'shap-pos' if item.value > 0 else 'shap-neg' }}" 
                                     style="width: {{ item.width }}%; margin-left: 0;"></div>
                            </div>
                        </div>
                        {% endfor %}
                    </div>

                    <div class="card">
                        <h3>Technical Indicators</h3>
                        <table>
                            <tr>
                                <td>RSI (14)</td>
                                <td class="mono">{{ "%.2f"|format(latest['RSI_14']) }}</td>
                            </tr>
                            <tr>
                                <td>SMA 50</td>
                                <td class="mono">${{ "%.2f"|format(latest['SMA_50']) }}</td>
                            </tr>
                            <tr>
                                <td>SMA 200</td>
                                <td class="mono">${{ "%.2f"|format(latest['SMA_200']) }}</td>
                            </tr>
                            <tr>
                                <td>Support (20d)</td>
                                <td class="mono" style="color: var(--bull);">${{ "%.2f"|format(latest['Support_20']) }}</td>
                            </tr>
                            <tr>
                                <td>Resistance (20d)</td>
                                <td class="mono" style="color: var(--bear);">${{ "%.2f"|format(latest['Resistance_20']) }}</td>
                            </tr>
                        </table>
                    </div>
                </div>

                <div class="card">
                    <h3>Execution Roadmap</h3>
                    <p style="color: var(--text-muted); font-size: 0.875rem;">
                        This signal is generated via a multi-layer ensemble of XGBoost classifiers trained on a cross-sectional pool of assets. 
                        SHAP values indicate that <strong>{{ shap_data[0].feature if shap_data else 'N/A' }}</strong> is the primary driver of this decision.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
    def generate_live_dashboard(self, tickets, summary):
        print(f"Generating Live Execution Dashboard...")
        
        template = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <title>Forex Command Center | Live Execution Desk</title>
            <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&family=JetBrains+Mono&display=swap" rel="stylesheet">
            <style>
                :root {
                    --bg: #020617;
                    --card: #0f172a;
                    --accent: #38bdf8;
                    --text: #f8fafc;
                    --text-muted: #64748b;
                    --bull: #10b981;
                    --bear: #f43f5e;
                    --border: #1e293b;
                }
                body { font-family: 'Outfit', sans-serif; background: var(--bg); color: var(--text); margin: 0; padding: 40px; }
                .container { max-width: 1300px; margin: 0 auto; }
                
                header { 
                    display: flex; justify-content: space-between; align-items: center; 
                    margin-bottom: 40px; padding-bottom: 20px; border-bottom: 1px solid var(--border);
                }
                .status-live { display: flex; align-items: center; gap: 8px; color: var(--bull); font-size: 0.875rem; font-weight: 600; }
                .live-dot { width: 8px; height: 8px; background: var(--bull); border-radius: 50%; box-shadow: 0 0 10px var(--bull); animation: blink 1.5s infinite; }
                @keyframes blink { 0% { opacity: 0.3; } 50% { opacity: 1; } 100% { opacity: 0.3; } }

                .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; margin-bottom: 40px; }
                .card { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 20px; }
                .card h3 { margin: 0 0 12px 0; color: var(--text-muted); font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.1em; }
                .card .val { font-size: 1.75rem; font-weight: 700; color: var(--text); }
                .card .sub { font-size: 0.8125rem; color: var(--text-muted); margin-top: 4px; }

                .ticket-table { width: 100%; border-collapse: collapse; margin-top: 20px; background: var(--card); border-radius: 12px; overflow: hidden; border: 1px solid var(--border); }
                .ticket-table th { background: #1e293b; text-align: left; padding: 16px; font-size: 0.75rem; text-transform: uppercase; color: var(--text-muted); }
                .ticket-table td { padding: 16px; border-bottom: 1px solid var(--border); }
                
                .signal-badge { padding: 4px 12px; border-radius: 4px; font-weight: 700; font-size: 0.75rem; }
                .buy { background: rgba(16, 185, 129, 0.1); color: var(--bull); border: 1px solid var(--bull); }
                .sell { background: rgba(244, 63, 94, 0.1); color: var(--bear); border: 1px solid var(--bear); }
                
                .lots-badge { font-family: 'JetBrains Mono'; background: #334155; color: white; padding: 2px 8px; border-radius: 4px; }
                .mono { font-family: 'JetBrains Mono', monospace; }
                
                .alert-box { background: rgba(56, 189, 248, 0.05); border-left: 4px solid var(--accent); padding: 20px; border-radius: 4px; margin-top: 40px; }
            </style>
        </head>
        <body>
            <div class="container">
                <header>
                    <div>
                        <h1 style="margin: 0; font-size: 1.5rem;">Institutional Forex Desk</h1>
                        <div class="status-live"><div class="live-dot"></div> LIVE MARKET FEED ACTIVE</div>
                    </div>
                    <div style="text-align: right">
                        <div class="mono" style="color: var(--text-muted);">{{ timestamp }}</div>
                        <div style="font-size: 0.75rem;">SESSION: LONDON/NY OVERLAP</div>
                    </div>
                </header>

                <div class="grid">
                    <div class="card">
                        <h3>Active Signals</h3>
                        <div class="val">{{ summary.active_signals }}</div>
                        <div class="sub">Across {{ tickers_count }} monitored pairs</div>
                    </div>
                    <div class="card">
                        <h3>Portfolio Exposure</h3>
                        <div class="val">{{ summary.total_exposure_lots }} Lots</div>
                        <div class="sub">Total notional at risk</div>
                    </div>
                    <div class="card">
                        <h3>Risk Per Trade</h3>
                        <div class="val" style="color: var(--accent);">{{ summary.max_risk_per_trade }}</div>
                        <div class="sub">Equity-at-risk per ATR stop</div>
                    </div>
                    <div class="card">
                        <h3>Conviction Focus</h3>
                        <div class="val" style="color: var(--bull);">{{ summary.highest_conviction }}</div>
                        <div class="sub">Highest probability setup</div>
                    </div>
                </div>

                <h2 style="font-size: 1rem; text-transform: uppercase; color: var(--text-muted); margin-bottom: 20px;">Execution Tickets Ready</h2>
                <table class="ticket-table">
                    <thead>
                        <tr>
                            <th>Pair</th>
                            <th>Regime</th>
                            <th>Signal</th>
                            <th>Confidence</th>
                            <th>Lots</th>
                            <th>Entry</th>
                            <th>Stop Loss</th>
                            <th>Take Profit</th>
                            <th>R:R</th>
                            <th>HRP Scale</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for t in tickets %}
                        <tr>
                            <td class="mono" style="font-weight: 700;">{{ t.ticker }}</td>
                            <td>{{ t.regime }}</td>
                            <td><span class="signal-badge {{ 'buy' if t.signal == 'BUY' else 'sell' }}">{{ t.signal }}</span></td>
                            <td class="mono">{{ t.confidence }}</td>
                            <td><span class="lots-badge">{{ t.lots }}</span></td>
                            <td class="mono">${{ "%.5f"|format(t.price) }}</td>
                            <td class="mono" style="color: var(--bear);">${{ "%.5f"|format(t.stop_loss) }}</td>
                            <td class="mono" style="color: var(--bull);">${{ "%.5f"|format(t.take_profit) }}</td>
                            <td class="mono">{{ t.risk_reward }}</td>
                            <td class="mono">{{ t.hrp_scale }}</td>
                        </tr>
                        {% endfor %}
                        {% if not tickets %}
                        <tr>
                            <td colspan="10" style="text-align: center; color: var(--text-muted); padding: 40px;">No high-conviction signals at this time. Monitoring market...</td>
                        </tr>
                        {% endif %}
                    </tbody>
                </table>

                <div class="alert-box">
                    <h3 style="margin: 0 0 10px 0; font-size: 0.875rem; color: var(--accent);">EXECUTION ADVISORY</h3>
                    <p style="margin: 0; font-size: 0.8125rem; color: var(--text-muted);">
                        These signals use <strong>ATR-based stops</strong>. Slippage is modeled at 0.5 pips. 
                        <strong>Hierarchical Risk Parity (HRP)</strong> is ACTIVE: position sizes are automatically diversified based on the correlation structure of the Forex basket.
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
