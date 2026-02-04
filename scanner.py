import yfinance as yf
import pandas as pd
import pandas_ta as ta
import json
from datetime import datetime

def get_expanded_tickers():
    """Pulls a wide variety of stocks (~600+ high-volume stocks)"""
    try:
        # S&P 500
        sp500 = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')[0]['Symbol'].tolist()
        # Nasdaq 100
        nasdaq100 = pd.read_html('https://en.wikipedia.org/wiki/Nasdaq-100')[4]['Ticker'].tolist()
        
        tickers = list(set(sp500 + nasdaq100))
        # Clean tickers (some use dots like BRK.B, yfinance prefers BRK-B)
        return [t.replace('.', '-') for t in tickers]
    except Exception as e:
        print(f"Error fetching ticker list: {e}")
        return ["AAPL", "MSFT", "TSLA", "NVDA", "AMD", "GOOGL", "AMZN"] # Fallback

def scan():
    tickers = get_expanded_tickers()
    print(f"Scanning {len(tickers)} stocks...")
    
    # Download data in one batch for speed
    data = yf.download(tickers, period="60d", interval="1d", group_by='ticker', threads=True)
    
    picks = []
    for ticker in tickers:
        try:
            df = data[ticker].dropna()
            if len(df) < 50: continue

            # --- Technical Analysis ---
            df['RSI'] = ta.rsi(df['Close'], length=14)
            df['SMA_20'] = ta.sma(df['Close'], length=20)
            df['SMA_50'] = ta.sma(df['Close'], length=50)
            avg_vol = df['Volume'].tail(20).mean()
            
            last = df.iloc[-1]
            prev = df.iloc[-2]

            # --- Improved Picking Strategy ---
            # Signal 1: RSI Divergence/Oversold (Price potentially bottoming)
            is_oversold = last['RSI'] < 35 
            
            # Signal 2: Trend Reversal (Price crosses above 20 SMA)
            is_reversal = prev['Close'] < prev['SMA_20'] and last['Close'] > last['SMA_20']
            
            # Signal 3: Volume Confirmation (More buying than usual)
            is_volume_spike = last['Volume'] > (avg_vol * 1.5)

            if (is_oversold and is_reversal) or (is_reversal and is_volume_spike):
                score = sum([is_oversold, is_reversal, is_volume_spike])
                picks.append({
                    "ticker": ticker,
                    "price": round(last['Close'], 2),
                    "score": score,
                    "reason": "Oversold Reversal" if is_oversold else "Trend Breakout",
                    "rsi": round(last['RSI'], 1)
                })
        except:
            continue

    # Sort by score (strongest signals first) and pick top 15
    picks = sorted(picks, key=lambda x: x['score'], reverse=True)[:15]
    
    output = {
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "picks": picks
    }
    
    with open('data.json', 'w') as f:
        json.dump(output, f, indent=4)
    print(f"Scan complete. Found {len(picks)} high-quality picks.")

if __name__ == "__main__":
    scan()
