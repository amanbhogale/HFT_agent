import requests
import os

API_KEY = os.getenv("GEMINI_API_KEY")
url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

headers = {
    "Content-Type": "application/json",
    "X-goog-api-key": API_KEY
}
data = {
    "contents": [
        {
            "parts": [
                {"text": "Hello, how are you?"}
            ]
        }
    ]
}

response = requests.post(url, json=data, headers=headers)
print("Status code:", response.status_code)
print("Response JSON:", response.json())

