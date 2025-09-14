''' hello '''
import os
import requests
from .state import State

API_KEY = os.getenv("GEMINI_API_KEY")

def call_gemini_api(prompt: str) -> str:
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
    headers = {
        "Content-Type": "application/json",
        "X-goog-api-key": API_KEY
    }
    data = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }
    response = requests.post(url, json=data, headers=headers)
    if response.status_code == 200:
        result = response.json()
        return result["candidates"][0]["content"] if "candidates" in result else "No response"
    else:
        return f"Error: {response.status_code} {response.text}"

def gemini_chat_tool(state: State) -> State:
    user_message = state["messages"][-1]
    bot_reply = call_gemini_api(user_message)
    state["messages"].append(bot_reply)
    return state

