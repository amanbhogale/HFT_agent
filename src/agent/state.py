"""
Module for agent functions and orchestrations in LangGraph.

Contains functions and classes to define nodes, tools, and workflow logic for the agent.
"""

#state defination for the agent 
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph , START , END
from langgraph.graph.message import add_messages



class State(TypedDict):
    messages : Annotated[list , add_messages]
