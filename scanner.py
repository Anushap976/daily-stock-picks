import yfinance as yf
import pandas as pd
import json
from datetime import datetime

def get_tickers():
    """Combines S&P 500 and Nasdaq 100 for a wide scan."""
    try:
        sp500 = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')[0]['Symbol'].tolist()
        nasdaq100 = pd.read_html('https://en.wikipedia.org/wiki/Nasdaq-100')[4]['Ticker'].tolist()
        tickers = list(set(sp500 + nasdaq100))
        return [t.replace('.', '-') for t in tickers if isinstance(t, str)]
    except:
        return ["AAPL", "MSFT", "TSLA", "NVDA", "AMD", "GOOGL", "AMZN", "META", "NFLX", "PLTR"]

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / (loss + 1e-9)
    return 100 - (100 / (1 + rs))

def scan():
    tickers = get_tickers()
    print(f"Scanning {len(tickers)} stocks every 5 minutes...")
    
    # Download 90 days of data for technicals
    data = yf.download(tickers, period="90d", interval="1d", group_by='ticker', threads=True)
    
    all_results = []
    for ticker in tickers:
        try:
            df = data[ticker].dropna()
            if len(df) < 50: continue

            close = df['Close']
            df['RSI'] = calculate_rsi(close)
            df['SMA_20'] = close.rolling(window=20).mean()
            df['SMA_50'] = close.rolling(window=50).mean()
            avg_vol = df['Volume'].tail(20).mean()
            
            last = df.iloc[-1]
            prev = df.iloc[-2]

            # --- 5-POINT SCORING SYSTEM ---
            score = 0
            reasons = []

            if last['RSI'] < 30: score += 2; reasons.append("Deeply Oversold")
            elif last['RSI'] < 45: score += 1; reasons.append("Low RSI")
            
            if last['Close'] > last['SMA_20'] and prev['Close'] < prev['SMA_20']:
                score += 2; reasons.append("Price Cross SMA20")
            
            if last['Volume'] > (avg_vol * 1.5):
                score += 1; reasons.append("High Volume")

            if score >= 2: # Only include stocks with at least 2 points
                all_results.append({
                    "ticker": ticker,
                    "price": round(float(last['Close']), 2),
                    "score": score,
                    "reason": ", ".join(reasons),
                    "rsi": round(float(last['RSI']), 1)
                })
        except:
            continue

    # Sort by highest score first
    top_picks = sorted(all_results, key=lambda x: x['score'], reverse=True)[:25]
    
    output = {
        "last_updated": datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
        "picks": top_picks
    }
    
    with open('data.json', 'w') as f:
        json.dump(output, f, indent=4)
    print(f"Success! Found {len(top_picks)} picks.")

if __name__ == "__main__":
    scan()
