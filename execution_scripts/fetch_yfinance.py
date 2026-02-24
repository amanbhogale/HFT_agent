#!/usr/bin/env python3
"""
fetch_yfinance.py
Uses the free yfinance library (no API key needed).
"""

import json
import os
import datetime
import yfinance as yf  # pip install yfinance

OUTPUT_DIR = "./DATA"
TICKERS = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA",
           "BTC-USD", "ETH-USD", "SPY", "QQQ"]

os.makedirs(OUTPUT_DIR, exist_ok=True)


def fetch_and_save(ticker: str, period: str = "1mo") -> None:
    """Download recent data and merge into existing JSON."""
    filepath = os.path.join(OUTPUT_DIR, f"{ticker.replace('-', '_')}.json")

    # Download with yfinance
    stock = yf.Ticker(ticker)
    df = stock.history(period=period)

    if df.empty:
        print(f"⚠️  No data returned for {ticker}")
        return

    # Load existing
    existing_series = {}
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            existing_series = json.load(f).get("time_series", {})

    # Merge new data
    for date, row in df.iterrows():
        date_str = date.strftime("%Y-%m-%d")
        existing_series[date_str] = {
            "open": round(row["Open"], 4),
            "high": round(row["High"], 4),
            "low": round(row["Low"], 4),
            "close": round(row["Close"], 4),
            "volume": int(row["Volume"]),
        }

    result = {
        "ticker": ticker,
        "last_updated": datetime.datetime.now().isoformat(),
        "total_records": len(existing_series),
        "time_series": dict(sorted(existing_series.items(), reverse=True)),
    }

    with open(filepath, "w") as f:
        json.dump(result, f, indent=2)

    print(f"✅ {ticker}: {len(existing_series)} records → {filepath}")


if __name__ == "__main__":
    for t in TICKERS:
        fetch_and_save(t)
