import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
from hmmlearn.hmm import GaussianHMM
import jinja2
import os
import argparse

def fetch_data(ticker="AAPL", period="2y", interval="1d"):
    print(f"Fetching data for {ticker}...")
    df = yf.download(ticker, period=period, interval=interval)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(1)
    df.dropna(inplace=True)
    return df

def calculate_indicators(df):
    print("Calculating indicators...")
    # Moving Averages
    df['SMA_50'] = ta.sma(df['Close'], length=50)
    df['SMA_200'] = ta.sma(df['Close'], length=200)
    
    # RSI
    df['RSI_14'] = ta.rsi(df['Close'], length=14)
    
    # ATR for volatility
    df['ATR_14'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
    
    # Returns
    df['Returns'] = df['Close'].pct_change()
    df.dropna(inplace=True)
    return df

def detect_regimes(df):
    print("Detecting market regimes using HMM...")
    features = np.column_stack([df['Returns'].values, df['ATR_14'].values])
    
    model = GaussianHMM(n_components=2, covariance_type="full", n_iter=1000, random_state=42)
    model.fit(features)
    
    regimes = model.predict(features)
    df['Regime'] = regimes
    
    regime_means = df.groupby('Regime')['Returns'].mean()
    if regime_means[0] > regime_means[1]:
        regime_map = {0: 'Bullish', 1: 'Bearish'}
    else:
        regime_map = {0: 'Bearish', 1: 'Bullish'}
        
    df['Regime_Label'] = df['Regime'].map(regime_map)
    return df

def generate_report(ticker, df):
    print("Generating report...")
    latest = df.iloc[-1]
    
    template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>{{ ticker }} Quant Analysis Report</title>
        <style>
            :root {
                --primary: #1e3a8a;
                --bg: #f8fafc;
                --card-bg: #ffffff;
                --text: #334155;
                --border: #e2e8f0;
                --bullish: #10b981;
                --bearish: #ef4444;
            }
            body { 
                font-family: 'Inter', -apple-system, sans-serif; 
                margin: 0;
                padding: 40px; 
                background: var(--bg);
                color: var(--text);
            }
            .container {
                max-width: 900px;
                margin: 0 auto;
                background: var(--card-bg);
                padding: 40px;
                border-radius: 12px;
                box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
            }
            h1 { color: var(--primary); margin-top: 0; }
            h2 { color: var(--text); border-bottom: 2px solid var(--border); padding-bottom: 8px; margin-top: 32px; }
            table { border-collapse: collapse; width: 100%; margin-bottom: 20px; }
            th, td { border: 1px solid var(--border); padding: 12px; text-align: left; }
            th { background-color: var(--bg); font-weight: 600; width: 40%; }
            .bullish { color: var(--bullish); font-weight: bold; }
            .bearish { color: var(--bearish); font-weight: bold; }
            .neutral { color: var(--text); font-weight: bold; }
            .date-badge {
                display: inline-block;
                background: var(--primary);
                color: white;
                padding: 4px 12px;
                border-radius: 16px;
                font-size: 0.875rem;
                margin-bottom: 24px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>{{ ticker }} Quantitative Analysis Report</h1>
            <div class="date-badge">Report Date: {{ latest.name.strftime('%Y-%m-%d') }}</div>
            
            <h2>1. Current Market Regime</h2>
            <table>
                <tr>
                    <th>Current Price</th>
                    <td>${{ "%.2f"|format(latest['Close']) }}</td>
                </tr>
                <tr>
                    <th>Current Regime</th>
                    <td class="{{ latest['Regime_Label'] | lower }}">{{ latest['Regime_Label'] }}</td>
                </tr>
                <tr>
                    <th>SMA 50</th>
                    <td>${{ "%.2f"|format(latest['SMA_50']) }}</td>
                </tr>
                <tr>
                    <th>SMA 200</th>
                    <td>${{ "%.2f"|format(latest['SMA_200']) }}</td>
                </tr>
                <tr>
                    <th>RSI (14)</th>
                    <td>{{ "%.2f"|format(latest['RSI_14']) }}</td>
                </tr>
            </table>

            <h2>2. Technical Signals</h2>
            <table>
                <tr>
                    <th>Signal</th>
                    <th>Status</th>
                </tr>
                <tr>
                    <td>Trend (SMA50 vs SMA200)</td>
                    <td>
                        {% if latest['SMA_50'] > latest['SMA_200'] %}
                        <span class="bullish">Bullish (Golden Cross)</span>
                        {% else %}
                        <span class="bearish">Bearish (Death Cross)</span>
                        {% endif %}
                    </td>
                </tr>
                <tr>
                    <td>Momentum (RSI)</td>
                    <td>
                        {% if latest['RSI_14'] > 70 %}
                        <span class="bearish">Overbought</span>
                        {% elif latest['RSI_14'] < 30 %}
                        <span class="bullish">Oversold</span>
                        {% else %}
                        <span class="neutral">Neutral</span>
                        {% endif %}
                    </td>
                </tr>
            </table>
            
            <h2>3. Risk Metrics</h2>
            <table>
                <tr>
                    <th>Metric</th>
                    <th>Value</th>
                </tr>
                <tr>
                    <td>ATR (14)</td>
                    <td>{{ "%.2f"|format(latest['ATR_14']) }}</td>
                </tr>
                <tr>
                    <td>Daily Return</td>
                    <td>
                        {% set ret = latest['Returns'] * 100 %}
                        <span class="{{ 'bullish' if ret > 0 else 'bearish' }}">
                            {{ "%.2f"|format(ret) }}%
                        </span>
                    </td>
                </tr>
            </table>
        </div>
    </body>
    </html>
    """
    
    html = jinja2.Template(template).render(
        ticker=ticker,
        latest=latest
    )
    
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "dashboard", "reports")
    os.makedirs(output_dir, exist_ok=True)
    report_path = os.path.join(output_dir, f"{ticker}_report.html")
    with open(report_path, "w") as f:
        f.write(html)
    print(f"Report saved to {os.path.abspath(report_path)}")

def main():
    parser = argparse.ArgumentParser(description='Generate a quant report for a given ticker.')
    parser.add_argument('--ticker', type=str, default='AAPL', help='The stock ticker to analyze.')
    parser.add_argument('--period', type=str, default='2y', help='Data period to fetch.')
    args = parser.parse_args()

    df = fetch_data(args.ticker, args.period)
    df = calculate_indicators(df)
    df = detect_regimes(df)
    generate_report(args.ticker, df)

if __name__ == "__main__":
    main()
