"""
LangGraph single-node graph template for financial analysis.
Processes symbol input, fetches fundamentals, calculates ratios,
analyzes sentiment, builds graph data, and produces a visualization URL.
"""

from __future__ import annotations
from typing import Any, Dict, Optional, TypedDict
from langgraph.graph import StateGraph
from langgraph.runtime import Runtime

from src.state import State
from src.agents.tools import fetch_fundamentals, calculate_ratios, analyze_news_sentiment
from src.agents.graph_helpers import build_financial_graph, create_gemini_visualization

class Context(TypedDict):
    my_configurable_param: str

async def call_model(state: State, runtime: Runtime[Context]) -> Dict[str, Any]:
    """Main processing node for financial analysis."""
    try:
        symbol = state.get("symbol", "")
        if not symbol:
            return {
                "error": "No symbol provided",
                "symbol": symbol
            }

        # Fetch and process data
        fundamentals_df = fetch_fundamentals(symbol)
        ratios_df = calculate_ratios(fundamentals_df)

        # Example placeholder news for sentiment analysis
        sample_news = [
            {
                "headline": f"{symbol} quarterly report", 
                "summary": "Strong numbers."
            }
        ]
        sentiments = analyze_news_sentiment(sample_news)

        # Build graph and visualization
        graph_data = build_financial_graph(fundamentals_df, ratios_df, sentiments)
        viz_url = create_gemini_visualization(graph_data)

        return {
            "fundamentals": fundamentals_df.to_dict(orient="records") if not fundamentals_df.empty else [],
            "ratios": ratios_df.to_dict(orient="records") if not ratios_df.empty else [],
            "sentiments": sentiments,
            "visualization_url": viz_url,
            "symbol": symbol
        }
    except Exception as e:
        print(f"Error in call_model: {e}")
        return {
            "error": str(e),
            "symbol": state.get("symbol", "")
        }

# Create the graph
graph = (
    StateGraph(State, context_schema=Context)
    .add_node("call_model", call_model)
    .add_edge("__start__", "call_model")
    .compile(name="Financial Analysis Graph")
)

