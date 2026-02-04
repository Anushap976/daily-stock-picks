#!/usr/bin/env python3
"""
Daily Stock Picks Auto-Updater
Automatically analyzes stocks and updates website HTML files
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import re

# ========================
# CONFIGURATION
# ========================

# Stock universes to scan
SCAN_UNIVERSE = [
    # Tech
    'AAPL', 'MSFT', 'NVDA', 'GOOGL', 'META', 'TSLA', 'AMD', 'INTC',
    # Energy
    'XLE', 'XOP', 'OXY', 'CVX', 'COP',
    # Small Caps
    'IWM', 'VTWO',
    # Commodities
    'GLD', 'SLV', 'USO',
    # Semis
    'SOXX', 'SMH', 'SNDK',
    # Quantum/Speculative
    'RGTI', 'IONQ', 'QBTS',
]

# ========================
# TECHNICAL ANALYSIS
# ========================

def calculate_rsi(data, periods=14):
    """Calculate RSI indicator"""
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=periods).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=periods).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1]

def calculate_macd(data):
    """Calculate MACD indicator"""
    exp1 = data['Close'].ewm(span=12, adjust=False).mean()
    exp2 = data['Close'].ewm(span=26, adjust=False).mean()
    macd = exp1 - exp2
    signal = macd.ewm(span=9, adjust=False).mean()
    return macd.iloc[-1], signal.iloc[-1]

def get_moving_averages(data):
    """Calculate key moving averages"""
    ma50 = data['Close'].rolling(window=50).mean().iloc[-1]
    ma200 = data['Close'].rolling(window=200).mean().iloc[-1]
    return ma50, ma200

def analyze_stock(ticker):
    """Comprehensive stock analysis"""
    try:
        stock = yf.Ticker(ticker)
        
        # Get historical data
        hist = stock.history(period="1y")
        if len(hist) < 200:
            return None
        
        current_price = hist['Close'].iloc[-1]
        
        # Technical indicators
        rsi = calculate_rsi(hist)
        macd, macd_signal = calculate_macd(hist)
        ma50, ma200 = get_moving_averages(hist)
        
        # Volume analysis
        avg_volume = hist['Volume'].tail(20).mean()
        current_volume = hist['Volume'].iloc[-1]
        volume_ratio = current_volume / avg_volume
        
        # Price metrics
        high_52w = hist['High'].tail(252).max()
        low_52w = hist['Low'].tail(252).min()
        range_position = (current_price - low_52w) / (high_52w - low_52w) * 100
        
        # Support/Resistance
        recent_high = hist['High'].tail(50).max()
        recent_low = hist['Low'].tail(50).min()
        
        # PD Analysis (Premium/Discount)
        equilibrium = (recent_high + recent_low) / 2
        pd_position = (current_price - equilibrium) / (recent_high - equilibrium) * 100
        
        # Determine bias
        bullish_score = 0
        bearish_score = 0
        
        # RSI scoring
        if rsi < 30:
            bullish_score += 3  # Oversold = bullish
        elif rsi > 70:
            bearish_score += 3  # Overbought = bearish
        
        # MACD scoring
        if macd > macd_signal:
            bullish_score += 2
        else:
            bearish_score += 2
        
        # Moving average scoring
        if current_price > ma50 > ma200:
            bullish_score += 2  # Golden cross
        elif current_price < ma50 < ma200:
            bearish_score += 2  # Death cross
        
        # Volume scoring
        if volume_ratio > 1.5:
            bullish_score += 1 if current_price > hist['Close'].iloc[-2] else 0
            bearish_score += 1 if current_price < hist['Close'].iloc[-2] else 0
        
        # PD scoring
        if pd_position < -30:  # Deep discount
            bullish_score += 2
        elif pd_position > 70:  # Premium zone
            bearish_score += 2
        
        # Determine rating
        if bullish_score > bearish_score + 2:
            rating = "STRONG BUY" if bullish_score >= 7 else "BUY"
            bias = "bullish"
        elif bearish_score > bullish_score + 2:
            rating = "STRONG PUT" if bearish_score >= 7 else "PUT"
            bias = "bearish"
        else:
            rating = "NEUTRAL"
            bias = "neutral"
        
        return {
            'ticker': ticker,
            'price': round(current_price, 2),
            'rsi': round(rsi, 1),
            'macd': round(macd, 2),
            'macd_signal': round(macd_signal, 2),
            'ma50': round(ma50, 2),
            'ma200': round(ma200, 2),
            'volume': int(current_volume / 1_000_000),  # In millions
            'volume_ratio': round(volume_ratio, 2),
            'support': round(recent_low, 2),
            'resistance': round(recent_high, 2),
            'range_position': round(range_position, 1),
            'pd_position': round(pd_position, 1),
            'equilibrium': round(equilibrium, 2),
            'rating': rating,
            'bias': bias,
            'bullish_score': bullish_score,
            'bearish_score': bearish_score,
            'high_52w': round(high_52w, 2),
            'low_52w': round(low_52w, 2),
        }
    
    except Exception as e:
        print(f"Error analyzing {ticker}: {e}")
        return None

# ========================
# STOCK SELECTION
# ========================

def detect_parabolic_moves(results):
    """Detect parabolic tops (like SLV) and breakout rockets (like SNDK)"""
    
    parabolic_tops = []
    breakout_rockets = []
    
    for r in results:
        # Parabolic top detection (bearish)
        if r['range_position'] > 85 and r['rsi'] > 70:
            # Stock near 52-week high and overbought
            parabolic_tops.append({**r, 'pattern': 'PARABOLIC TOP'})
        
        # Breakout rocket detection (bullish)
        if r['volume_ratio'] > 2.0 and r['range_position'] > 70 and r['rsi'] < 75:
            # High volume breakout not yet overbought
            breakout_rockets.append({**r, 'pattern': 'BREAKOUT ROCKET'})
    
    return parabolic_tops, breakout_rockets

def select_top_picks():
    """Analyze universe and select top bullish and bearish picks"""
    
    print("🔍 Scanning stock universe...")
    results = []
    
    for ticker in SCAN_UNIVERSE:
        print(f"  Analyzing {ticker}...")
        analysis = analyze_stock(ticker)
        if analysis:
            results.append(analysis)
    
    # Detect special patterns
    parabolic_tops, breakout_rockets = detect_parabolic_moves(results)
    
    # Priority 1: Parabolic tops (bearish)
    # Priority 2: Regular bearish picks
    bearish_picks = parabolic_tops[:2]  # Take top 2 parabolic tops
    if len(bearish_picks) < 3:
        regular_bearish = sorted(
            [r for r in results if r['bias'] == 'bearish' and r not in parabolic_tops],
            key=lambda x: x['bearish_score'],
            reverse=True
        )
        bearish_picks.extend(regular_bearish[:3 - len(bearish_picks)])
    
    # Priority 1: Breakout rockets (bullish)
    # Priority 2: Regular bullish picks
    bullish_picks = breakout_rockets[:2]  # Take top 2 rockets
    if len(bullish_picks) < 3:
        regular_bullish = sorted(
            [r for r in results if r['bias'] == 'bullish' and r not in breakout_rockets],
            key=lambda x: x['bullish_score'],
            reverse=True
        )
        bullish_picks.extend(regular_bullish[:3 - len(bullish_picks)])
    
    return bullish_picks[:3], bearish_picks[:3]

# ========================
# HTML GENERATION
# ========================

def generate_stock_pick_html(pick, is_bearish=False):
    """Generate HTML for a single stock pick"""
    
    # Determine target based on resistance/support
    if is_bearish:
        target1 = pick['equilibrium']
        target2 = pick['support']
        entry = pick['price']
        stop = pick['resistance']
        class_name = 'bearish'
    else:
        target1 = pick['equilibrium'] if pick['price'] < pick['equilibrium'] else pick['resistance']
        target2 = pick['resistance']
        entry = pick['price']
        stop = pick['support']
        class_name = ''
    
    # Generate catalyst based on indicators
    catalysts = []
    if pick['rsi'] < 30:
        catalysts.append("Extreme oversold RSI")
    elif pick['rsi'] > 70:
        catalysts.append("Extreme overbought RSI")
    
    if abs(pick['macd']) > 1:
        if pick['macd'] > pick['macd_signal']:
            catalysts.append("Bullish MACD crossover")
        else:
            catalysts.append("Bearish MACD crossover")
    
    if pick['volume_ratio'] > 1.5:
        catalysts.append(f"High volume ({pick['volume_ratio']}x average)")
    
    if pick['price'] > pick['ma50'] > pick['ma200']:
        catalysts.append("Golden cross pattern")
    elif pick['price'] < pick['ma50'] < pick['ma200']:
        catalysts.append("Death cross pattern")
    
    catalyst_text = ". ".join(catalysts[:3]) if catalysts else "Technical setup aligning"
    
    html = f'''
                <div class="stock-pick {class_name}">
                    <div class="stock-header">
                        <span class="ticker">{pick['ticker']}</span>
                        <span class="rating">{pick['rating']}</span>
                    </div>
                    <div class="technical-data">
                        <div class="metric"><strong>RSI:</strong> {pick['rsi']}</div>
                        <div class="metric"><strong>MACD:</strong> {pick['macd']}</div>
                        <div class="metric"><strong>Price:</strong> ${pick['price']}</div>
                        <div class="metric"><strong>Target:</strong> ${target1}-{target2}</div>
                        <div class="metric"><strong>Support:</strong> ${pick['support']}</div>
                        <div class="metric"><strong>Volume:</strong> {pick['volume']}M</div>
                    </div>
                    <div class="catalyst">
                        <strong>📊 Catalyst:</strong> {catalyst_text}. Price at {pick['range_position']}% of 52-week range.
                    </div>
                </div>
'''
    return html

def update_html_file(bullish_picks, bearish_picks):
    """Update index.html with new picks"""
    
    # Read current HTML
    with open('index.html', 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Generate new picks HTML
    bullish_html = '\n'.join([generate_stock_pick_html(p) for p in bullish_picks])
    bearish_html = '\n'.join([generate_stock_pick_html(p, is_bearish=True) for p in bearish_picks])
    
    # Update timestamp
    timestamp = datetime.now().strftime("%B %d, %Y - %I:%M %p EST")
    
    # Replace bullish section (between specific markers)
    bullish_pattern = r'(<h2>🚀 Bullish Picks - Next Week</h2>)(.*?)(</div>\s*<div class="card">\s*<h2>📉 Bearish Picks)'
    html_content = re.sub(
        bullish_pattern,
        f'\\1\n{bullish_html}\n                \\3',
        html_content,
        flags=re.DOTALL
    )
    
    # Replace bearish section
    bearish_pattern = r'(<h2>📉 Bearish Picks - Put Opportunities</h2>)(.*?)(</div>\s*</div>\s*<!-- MARKET INTELLIGENCE)'
    html_content = re.sub(
        bearish_pattern,
        f'\\1\n{bearish_html}\n                \\3',
        html_content,
        flags=re.DOTALL
    )
    
    # Write updated HTML
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ Updated index.html with {len(bullish_picks)} bullish and {len(bearish_picks)} bearish picks")

# ========================
# MAIN EXECUTION
# ========================

def main():
    """Main execution function"""
    print("=" * 50)
    print("🤖 DAILY STOCK PICKS AUTO-UPDATER")
    print("=" * 50)
    print(f"⏰ Running at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Select top picks
    bullish_picks, bearish_picks = select_top_picks()
    
    print("\n📊 SELECTED PICKS:")
    print("\n🚀 BULLISH:")
    for pick in bullish_picks:
        print(f"  {pick['ticker']}: {pick['rating']} (Score: {pick['bullish_score']}, RSI: {pick['rsi']}, Price: ${pick['price']})")
    
    print("\n📉 BEARISH:")
    for pick in bearish_picks:
        print(f"  {pick['ticker']}: {pick['rating']} (Score: {pick['bearish_score']}, RSI: {pick['rsi']}, Price: ${pick['price']})")
    
    # Update HTML files
    print("\n📝 Updating website...")
    update_html_file(bullish_picks, bearish_picks)
    
    print("\n✅ AUTO-UPDATE COMPLETE!")
    print("=" * 50)

if __name__ == "__main__":
    main()
