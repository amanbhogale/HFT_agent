"""Helper functions for graph building and visualization."""

import os
import requests
import pandas as pd
from typing import Dict, List, Any, Optional

def build_financial_graph(ratios_df: pd.DataFrame, sentiments: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Constructs a graph dictionary with nodes and edges representing financial ratios and news sentiments.
    """
    try:
        nodes = []
        edges = []

        # Create nodes for ratios with formatted labels
        if not ratios_df.empty:
            for idx, row in ratios_df.iterrows():
                node_id = f"ratio_node_{idx}"
                # Check if columns exist before accessing
                eps = row.get('EPS', 0.0)
                pe = row.get('P/E', 0.0)
                label = f"EPS: {eps:.2f}, P/E: {pe:.2f}"
                nodes.append({"id": node_id, "label": label})

        # Create nodes for sentiments (news headlines + sentiment label)
        for i, sentiment in enumerate(sentiments):
            nodes.append({
                "id": f"sentiment_{i}",
                "label": sentiment.get('headline', f'News {i}'),
                "properties": {
                    "sentiment": sentiment.get('sentiment', {}).get('label', 'NEUTRAL')
                }
            })

        # Connect ratio nodes to sentiment nodes
        ratio_count = len(ratios_df) if not ratios_df.empty else 0
        sentiment_count = len(sentiments)

        for i in range(min(ratio_count, sentiment_count)):
            edges.append({
                "source": f"ratio_node_{i}",
                "target": f"sentiment_{i}"
            })

        return {"nodes": nodes, "edges": edges}
    except Exception as e:
        print(f"Error building financial graph: {e}")
        return {"nodes": [], "edges": []}

def create_gemini_visualization(graph_data: Dict[str, Any]) -> Optional[str]:
    """
    Creates a simple text-based visualization since Gemini doesn't have a direct visualization API.
    In a real implementation, you would use a proper visualization library or service.
    """
    try:
        # This is a mock implementation since the original API doesn't exist
        # In practice, you might use libraries like plotly, networkx, or similar

        nodes = graph_data.get("nodes", [])
        edges = graph_data.get("edges", [])

        viz_text = "Financial Analysis Visualization:\n"
        viz_text += f"Nodes: {len(nodes)}\n"
        viz_text += f"Edges: {len(edges)}\n"

        if nodes:
            viz_text += "\nRatio Nodes:\n"
            for node in nodes:
                if "ratio_node" in node.get("id", ""):
                    viz_text += f"- {node.get('label', 'Unknown')}\n"

        # For a real implementation, you would:
        # 1. Use a proper graph visualization library
        # 2. Save the graph as an image
        # 3. Upload to a hosting service
        # 4. Return the URL

        # Mock URL for demonstration
        return f"mock://visualization/{hash(str(graph_data)) % 10000}"

    except Exception as e:
        print(f"Error creating visualization: {e}")
        return None

