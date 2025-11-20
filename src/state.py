"""State management for LangGraph Agent."""

from typing import Dict, List, Optional, Any, TypedDict

class State(TypedDict, total=False):
    """State schema for the financial analysis agent."""
    messages: List[str]
    symbol: Optional[str]
    ratios: Optional[Dict[str, Any]]
    fundamental_data: Optional[Dict[str, Any]]
    technical_data: Optional[Dict[str, Any]]
    price_data: Optional[Dict[str, Any]]
    sentiment_data: Optional[List[Dict[str, Any]]]
    visualization_url: Optional[str]

