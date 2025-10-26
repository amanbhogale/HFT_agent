import os
import requests
import pandas as pd
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
    return pd.DataFrame(data.get('data', []))

def calculate_ratios(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "netIncome" in df.columns and "sharesOutstanding" in df.columns and "marketCapitalization" in df.columns:
        # Calculate EPS with zero-division protection
        df['EPS'] = df['netIncome'] / df['sharesOutstanding'].replace(0, float('nan'))
        # Calculate P/E as market cap / (net income) - this gives market cap per dollar of earnings
        # Note: Traditional P/E is stock price / EPS, but this approximates the same concept
        df['P/E'] = df['marketCapitalization'] / df['netIncome'].replace(0, float('nan'))
    else:
        df['EPS'] = None
        df['P/E'] = None
    return df[['EPS', 'P/E']]

def analyze_news_sentiment(news_items: list) -> list:
    results = []
    for news in news_items:
        text = news.get('headline', '') + " " + news.get('summary', '')
        sentiment = sentiment_analyzer(text)[0]
        results.append({'headline': news.get('headline', ''), 'sentiment': sentiment})
    return results

