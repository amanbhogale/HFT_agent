import requests
import os

FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")
symbol = "AAPL"
url = f"https://finnhub.io/api/v1/stock/financials-reported?symbol={symbol}&token={FINNHUB_API_KEY}"

response = requests.get(url)
print("Status code:", response.status_code)
print("Response JSON:", response.json())

