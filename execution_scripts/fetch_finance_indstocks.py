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

OUTPUT_DIR = "./IND_STOCKS_5MIN"
# ============================================================================

# NIFTY 50 Stocks (NSE - National Stock Exchange)
NIFTY_50 = [
    "RELIANCE.NS",      # Reliance Industries
    "TCS.NS",           # Tata Consultancy Services
    "HDFCBANK.NS",      # HDFC Bank
    "INFY.NS",          # Infosys
    "ICICIBANK.NS",     # ICICI Bank
    "HINDUNILVR.NS",    # Hindustan Unilever
    "ITC.NS",           # ITC Limited
    "SBIN.NS",          # State Bank of India
    "BHARTIARTL.NS",    # Bharti Airtel
    "BAJFINANCE.NS",    # Bajaj Finance
    "KOTAKBANK.NS",     # Kotak Mahindra Bank
    "LT.NS",            # Larsen & Toubro
    "HCLTECH.NS",       # HCL Technologies
    "AXISBANK.NS",      # Axis Bank
    "ASIANPAINT.NS",    # Asian Paints
    "MARUTI.NS",        # Maruti Suzuki
    "SUNPHARMA.NS",     # Sun Pharma
    "TITAN.NS",         # Titan Company
    "WIPRO.NS",         # Wipro
    "ULTRACEMCO.NS",    # UltraTech Cement
    "NESTLEIND.NS",     # Nestle India
    "NTPC.NS",          # NTPC
    "TATASTEEL.NS",     # Tata Steel
    "TECHM.NS",         # Tech Mahindra
    "POWERGRID.NS",     # Power Grid Corporation
    "M&M.NS",           # Mahindra & Mahindra
    "ADANIPORTS.NS",    # Adani Ports
    "BAJAJFINSV.NS",    # Bajaj Finserv
    "ONGC.NS",          # ONGC
    "COALINDIA.NS",     # Coal India
    "INDUSINDBK.NS",    # IndusInd Bank
    "TMPV.NS",    # Tata Motors
    "DIVISLAB.NS",      # Divi's Laboratories
    "CIPLA.NS",         # Cipla
    "DRREDDY.NS",       # Dr. Reddy's Labs
    "EICHERMOT.NS",     # Eicher Motors
    "HEROMOTOCO.NS",    # Hero MotoCorp
    "BRITANNIA.NS",     # Britannia Industries
    "GRASIM.NS",        # Grasim Industries
    "HINDALCO.NS",      # Hindalco Industries
    "JSWSTEEL.NS",      # JSW Steel
    "APOLLOHOSP.NS",    # Apollo Hospitals
    "ADANIENT.NS",      # Adani Enterprises
    "BPCL.NS",          # Bharat Petroleum
    "SBILIFE.NS",       # SBI Life Insurance
    "TATACONSUM.NS",    # Tata Consumer Products
    "UPL.NS",           # UPL Limited
    "BAJAJ-AUTO.NS",    # Bajaj Auto
    "LTIM.NS",          # LTIMindtree
    "HDFCLIFE.NS",      # HDFC Life Insurance
]

# NIFTY Next 50 (High potential stocks)
NIFTY_NEXT_50 = [
    "ADANIGREEN.NS",    # Adani Green Energy
    "ADANIPOWER.NS",    # Adani Power
    "AMBUJACEM.NS",     # Ambuja Cements
    "BANDHANBNK.NS",    # Bandhan Bank
    "BERGEPAINT.NS",    # Berger Paints
    "BIOCON.NS",        # Biocon
    "BOSCHLTD.NS",      # Bosch
    "CHOLAFIN.NS",      # Cholamandalam Finance
    "COLPAL.NS",        # Colgate-Palmolive
    "DABUR.NS",         # Dabur India
    "DLF.NS",           # DLF Limited
    "GODREJCP.NS",      # Godrej Consumer
    "GAIL.NS",          # GAIL India
    "HAVELLS.NS",       # Havells India
    "ICICIPRULI.NS",    # ICICI Prudential Life
    "INDIGO.NS",        # InterGlobe Aviation
    "IOC.NS",           # Indian Oil Corporation
    "JINDALSTEL.NS",    # Jindal Steel & Power
    "MCDOWELL-N.NS",    # United Spirits
    "NAUKRI.NS",        # Info Edge (Naukri.com)
    "NMDC.NS",          # NMDC
    "OFSS.NS",          # Oracle Financial Services
    "PAGEIND.NS",       # Page Industries
    "PEL.NS",           # Piramal Enterprises
    "PETRONET.NS",      # Petronet LNG
    "PIDILITIND.NS",    # Pidilite Industries
    "PNB.NS",           # Punjab National Bank
    "SIEMENS.NS",       # Siemens
    "SRF.NS",           # SRF Limited
    "TORNTPHARM.NS",    # Torrent Pharma
    "TRENT.NS",         # Trent
    "VEDL.NS",          # Vedanta
    "VOLTAS.NS",        # Voltas
    "ZEEL.NS",          # Zee Entertainment
    "YESBANK.NS",       # Yes Bank
]

# Banking Sector
BANKING_STOCKS = [
    "HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "KOTAKBANK.NS",
    "AXISBANK.NS", "INDUSINDBK.NS", "BANDHANBNK.NS", "PNB.NS",
    "BANKBARODA.NS", "CANBK.NS", "IDFCFIRSTB.NS", "FEDERALBNK.NS",
]

# IT Sector
IT_STOCKS = [
    "TCS.NS", "INFY.NS", "HCLTECH.NS", "WIPRO.NS",
    "TECHM.NS", "LTIM.NS", "MPHASIS.NS", "COFORGE.NS",
    "PERSISTENT.NS", "MINDTREE.NS",
]

# Pharma Sector
PHARMA_STOCKS = [
    "SUNPHARMA.NS", "DIVISLAB.NS", "CIPLA.NS", "DRREDDY.NS",
    "BIOCON.NS", "TORNTPHARM.NS", "AUROPHARMA.NS", "LUPIN.NS",
    "CADILAHC.NS", "ALKEM.NS",
]

# Automobiles
AUTO_STOCKS = [
    "MARUTI.NS", "TATAMOTORS.NS", "M&M.NS", "EICHERMOT.NS",
    "HEROMOTOCO.NS", "BAJAJ-AUTO.NS", "ASHOKLEY.NS", "ESCORTS.NS",
    "TVSMOTOR.NS", "MOTHERSON.NS",
]

# BSE (Bombay Stock Exchange) - Same stocks, different suffix
# Example: RELIANCE.BO instead of RELIANCE.NS

BSE_TOP_STOCKS = [
    "RELIANCE.BO", "TCS.BO", "HDFCBANK.BO", "INFY.BO",
    "ICICIBANK.BO", "HINDUNILVR.BO", "ITC.BO", "SBIN.BO",
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
    for t in NIFTY_50:
        fetch_and_save(t)
