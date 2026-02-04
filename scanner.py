import yfinance as yf
import pandas as pd
import json
from datetime import datetime

def get_expanded_tickers():
    """Pulls S&P 500 and Nasdaq 100 tickers."""
    try:
        sp500 = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')[0]['Symbol'].tolist()
        nasdaq100 = pd.read_html('https://en.wikipedia.org/wiki/Nasdaq-100')[4]['Ticker'].tolist()
        tickers = list(set(sp500 + nasdaq100))
        return [t.replace('.', '-') for t in tickers]
    except:
        return ["AAPL", "MSFT", "TSLA", "NVDA", "AMD", "GOOGL", "AMZN", "META"]

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def scan():
    tickers = get_expanded_tickers()
    print(f"Scanning {len(tickers)} stocks...")
    
    # Batch download
    data = yf.download(tickers, period="60d", interval="1d", group_by='ticker', threads=True)
    
    picks = []
    for ticker in tickers:
        try:
            df = data[ticker].dropna()
            if len(df) < 50: continue

            # Technical Analysis (Manual calculation to avoid library errors)
            close = df['Close']
            df['RSI'] = calculate_rsi(close)
            df['SMA_20'] = close.rolling(window=20).mean()
            df['SMA_50'] = close.rolling(window=50).mean()
            avg_vol = df['Volume'].tail(20).mean()
            
            last = df.iloc[-1]
            prev = df.iloc[-2]

            # Logic
            is_oversold = last['RSI'] < 35 
            is_reversal = prev['Close'] < prev['SMA_20'] and last['Close'] > last['SMA_20']
            is_volume_spike = last['Volume'] > (avg_vol * 1.5)

            if (is_oversold and is_reversal) or (is_reversal and is_volume_spike):
                score = 1
                if is_oversold: score += 1
                if is_volume_spike: score += 1
                
                picks.append({
                    "ticker": ticker,
                    "price": round(float(last['Close']), 2),
                    "score": score,
                    "reason": "Oversold Reversal" if is_oversold else "Trend Breakout",
                    "rsi": round(float(last['RSI']), 1)
                })
        except:
            continue

    # Sort and save
    picks = sorted(picks, key=lambda x: x['score'], reverse=True)[:15]
    output = {"last_updated": datetime.now().strftime("%Y-%m-%d %H:%M"), "picks": picks}
    
    with open('data.json', 'w') as f:
        json.dump(output, f, indent=4)
    print("Done!")

if __name__ == "__main__":
    scan()
