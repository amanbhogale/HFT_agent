"""
Module for agent functions and orchestrations in LangGraph.

Contains functions and classes to define nodes, tools, and workflow logic for the agent.
"""

#main agent building code
from .state import State
from .tools import gemini_chat_tool

def run_chatbot():
    state: State = {"messages": []}
    print("Gemini Chatbot (type 'exit' to quit)")
    while True:
        user_input = input("You: ")
        if user_input.lower() == "exit":
            break
        state["messages"].append(user_input)
        state = gemini_chat_tool(state)
        print("Bot:", state["messages"][-1])

if __name__ == "__main__":
    run_chatbot()

