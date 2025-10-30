import os
import requests
import pandas as pd
import numpy as np
from transformers import pipeline
from src.state import State

API_KEY = os.getenv("GEMINI_API_KEY")
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")

#sentiment_analyzer = pipeline("sentiment-analysis")
sentiment_analyzer = pipeline(
    "sentiment-analysis",
    model="distilbert-base-uncased-finetuned-sst-2-english",
    revision="714eb0f",
    device=-1  # or device=0 if GPU available
)

def call_gemini_api(prompt: str) -> str:
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
    headers = {
        "Content-Type": "application/json",
        "X-goog-api-key": API_KEY
    }
    data = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    response = requests.post(url, json=data, headers=headers)
    if response.status_code == 200:
        result = response.json()
        return result.get("candidates", [{}])[0].get("content", "No response")
    else:
        return f"Error: {response.status_code} {response.text}"

def gemini_chat_tool(state: State) -> State:
    user_message = state.get("messages" , [""])[-1] if "messages" in state and state["messages"] else ""
    bot_reply = call_gemini_api(user_message)
    state.setdefault("messages" , []).append(bot_reply)
    return state


def fetch_fundamentals(symbol: str) -> pd.DataFrame:
    url = f'https://finnhub.io/api/v1/stock/financials-reported?symbol={symbol}&token={FINNHUB_API_KEY}'
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()
    if 'data' not in data:
        raise ValueError("No 'data' key in Finnhub response for fundamentals.")
    df_fundamentals = pd.DataFrame(data.get('data', []))
    return df_fundamentals


def fetch_current_price(symbol: str) -> float:
    url = f'https://finnhub.io/api/v1/quote?symbol={symbol}&token={FINNHUB_API_KEY}'
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()
    current_price = data.get('c')
    if current_price is None:
        raise ValueError(f"Could not fetch current price for symbol {symbol}")
    return current_price

def fetch_shares_and_market_cap(symbol: str) -> tuple[float ,float]:
    url = f'https://finnhub.io/api/v1/stock/metric?symbol={symbol}&metric=all&token={FINNHUB_API_KEY}'
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()
    metric = data.get('metric', {})
    shares_outstanding = metric.get('sharesOutstanding')
    market_cap = metric.get('marketCapitalization')

    if shares_outstanding is None:
        current_price = fetch_current_price(symbol)
        if current_price and market_cap:
            shares_outstanding = market_cap / current_price
            print(f"[INFO] Using fallback shares outstanding for {symbol}: {shares_outstanding}")
        else:
            raise ValueError(f"Missing sharesOutstanding and fallback calculation failed for {symbol}")

    return shares_outstanding, market_cap

shares, market_cap = fetch_shares_and_market_cap('NVDA')
print(f"Shares Outstanding: {shares}, Market Cap: {market_cap}")

def extract_financials(df: pd.DataFrame) -> pd.DataFrame:
    records = []
    for row in df.to_dict(orient="records"):
        report = row.get("report", {})
        ic = {item["concept"]: item["value"] for item in report.get("ic", [])} if "ic" in report else {}
        bs = {item["concept"]: item["value"] for item in report.get("bs", [])} if "bs" in report else {}
        row.update(ic)
        row.update(bs)
        records.append(row)
    return pd.DataFrame(records)

x = extract_financials(fetch_fundamentals("NVDA"))
print(x)


def calculate_ratios(df: pd.DataFrame, shares_outstanding: float, market_cap: float) -> pd.DataFrame:
    df = df.copy()
    if "us-gaap_NetIncomeLoss" in df.columns and shares_outstanding and market_cap:
        # Prevent division by zero or nan
        df["EPS"] = df["us-gaap_NetIncomeLoss"] / shares_outstanding
        df["P/E"] = market_cap / df["us-gaap_NetIncomeLoss"].replace(0, np.nan)
    else:
        df["EPS"] = None
        df["P/E"] = None
    return df[["year", "EPS", "P/E"]]



y = calculate_ratios(x , 3445.34 , 2345.23)
print(y)


def analyze_news_sentiment(news_items: list) -> list:
    results = []
    for news in news_items:
        text = news.get('headline', '') + " " + news.get('summary', '')
        sentiment = sentiment_analyzer(text)[0]
        results.append({'headline': news.get('headline', ''), 'sentiment': sentiment})
    return results
