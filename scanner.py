import yfinance as yf
import pandas as pd
import json
from datetime import datetime

def get_expanded_tickers():
    """Pulls S&P 500 and Nasdaq 100 tickers with a robust fallback."""
    try:
        # Try fetching from Wikipedia
        sp500 = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')[0]['Symbol'].tolist()
        nasdaq100 = pd.read_html('https://en.wikipedia.org/wiki/Nasdaq-100')[4]['Ticker'].tolist()
        tickers = list(set(sp500 + nasdaq100))
        return [t.replace('.', '-') for t in tickers if isinstance(t, str)]
    except Exception as e:
        print(f"Ticker fetch failed, using manual list. Error: {e}")
        return ["AAPL", "MSFT", "TSLA", "NVDA", "AMD", "GOOGL", "AMZN", "META", "NFLX", "PLTR", "SQ", "PYPL", "BA", "DIS", "JPM"]

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / (loss + 1e-9) # Avoid division by zero
    return 100 - (100 / (1 + rs))

def scan():
    tickers = get_expanded_tickers()
    print(f"Scanning {len(tickers)} stocks...")
    
    # Download data
    # We download 90 days to ensure enough data for 50-day SMAs
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

            # --- SCORING LOGIC (Higher is better) ---
            score = 0
            reasons = []

            # 1. RSI Oversold (Bottom Fishers)
            if last['RSI'] < 40: 
                score += 1
                reasons.append("Oversold")
            
            # 2. Price Momentum (Crossing 20 SMA)
            if last['Close'] > last['SMA_20'] and prev['Close'] < prev['SMA_20']:
                score += 2
                reasons.append("Trend Breakout")
            
            # 3. Volume Surge (Institutional interest)
            if last['Volume'] > (avg_vol * 1.3):
                score += 1
                reasons.append("Volume Spike")
            
            # 4. Golden Zone (Bullish alignment)
            if last['Close'] > last['SMA_20'] > last['SMA_50']:
                score += 1
                reasons.append("Bullish Trend")

            # We accept anything with a score > 0
            if score > 0:
                all_results.append({
                    "ticker": ticker,
                    "price": round(float(last['Close']), 2),
                    "score": score,
                    "reason": ", ".join(reasons),
                    "rsi": round(float(last['RSI']), 1)
                })
        except:
            continue

    # SORT BY SCORE and take the top 15
    # If no scores, it won't be empty if the market is open
    top_picks = sorted(all_results, key=lambda x: x['score'], reverse=True)[:15]
    
    output = {
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "picks": top_picks
    }
    
    with open('data.json', 'w') as f:
        json.dump(output, f, indent=4)
    
    print(f"Scan complete. Found {len(top_picks)} picks.")

if __name__ == "__main__":
    scan()
