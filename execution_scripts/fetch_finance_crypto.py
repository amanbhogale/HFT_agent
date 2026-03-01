#!/usr/bin/env python3
"""
fetch_yfinance.py
Uses the free yfinance library (no API key needed).
"""

import json
import os
import datetime
from textwrap import indent
from numpy._core import records
import yfinance as yf  # pip install yfinance

OUTPUT_DIR = "./crypto_data"
TICKERS = [
        "BTC-USD",      # Bitcoin
        "ETH-USD",      # Ethereum
        "BNB-USD",      # Binance Coin
        "XRP-USD",      # Ripple
        "ADA-USD",      # Cardano
        "DOGE-USD",     # Dogecoin
        "SOL-USD",      # Solana
        "MATIC-USD",    # Polygon
        "DOT-USD",      # Polkadot
        "AVAX-USD",     # Avalanche
    ]
os.makedirs(OUTPUT_DIR, exist_ok=True)



def fetch_and_save(ticker: str, period: str = "1mo", interval: str = "5m") -> None:
    """Download 5-minute interval data and merge into existing JSON."""
    filepath = os.path.join(OUTPUT_DIR, f"{ticker.replace('-', '_')}_5min.json")

    # Download with yfinance
    stock = yf.Ticker(ticker)
    
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=30)
    
    df = stock.history(
        start=start_date.strftime('%Y-%m-%d'),
        end=end_date.strftime('%Y-%m-%d'),
        interval=interval
    )
    
    if df.empty:
        print(f"No data retrieved for {ticker}")
        return
    
    # Reset index and rename the datetime column
    df = df.reset_index()
    
    # Handle column name (could be 'Datetime' or 'Date' depending on interval)
    datetime_col = 'Datetime' if 'Datetime' in df.columns else 'Date'
    
    # Convert datetime to string
    df[datetime_col] = df[datetime_col].astype(str)
    
    # Convert to list of dictionaries
    new_data = df.to_dict(orient='records')
    
    # Load existing data if file exists
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r') as f:
                existing_data = json.load(f)
            
            # Check if existing_data is a list
            if isinstance(existing_data, list) and len(existing_data) > 0:
                # Check if items are dictionaries
                if isinstance(existing_data[0], dict):
                    existing_dates = {record.get(datetime_col) for record in existing_data}
                    new_records = [r for r in new_data if r.get(datetime_col) not in existing_dates]
                    data = existing_data + new_records
                else:
                    # Existing data is not in expected format, replace it
                    data = new_data
            else:
                # Existing data is empty or not a list
                data = new_data
                
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Error reading existing file, creating new: {e}")
            data = new_data
    else:
        data = new_data
    
    # Save to JSON
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2, default=str)
    
    print(f"Saved {len(data)} records for {ticker}")
    print(f"Date range: {data[0].get(datetime_col)} to {data[-1].get(datetime_col)}")




if __name__ == "__main__":
    for t in TICKERS:
        fetch_and_save(t)
