"""
schemas/mongo_schemas.py
────────────────────────
Pydantic v2 models that define the shape of each MongoDB node document.
These are used:
  1. As validation before writes (loaders).
  2. As a reference for the collection JSON-Schema validator (see bottom).
"""

from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ══════════════════════════════════════════════════════════════════════════════
# Node: Asset
# ══════════════════════════════════════════════════════════════════════════════

class AssetNode(BaseModel):
    """
    Represents a tradeable crypto asset.
    Upsert key: ticker
    """
    ticker: str                          # e.g. "BTC"
    company_name: str                    # e.g. "Bitcoin"
    sector: str                          # e.g. "Layer 1", "DeFi", "Exchange"
    market_cap: Optional[float] = None   # USD
    price_usd: Optional[float] = None
    volume_24h: Optional[float] = None
    change_24h_pct: Optional[float] = None
    circulating_supply: Optional[float] = None
    total_supply: Optional[float] = None
    rank: Optional[int] = None
    source: str = "coingecko"
    ingested_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ══════════════════════════════════════════════════════════════════════════════
# Node: MacroEconomic
# ══════════════════════════════════════════════════════════════════════════════

class MacroEconomicNode(BaseModel):
    """
    A single macro indicator reading.
    Upsert key: (indicator, date)
    """
    indicator: str                       # e.g. "CPI", "FEDFUNDS"
    display_name: str                    # e.g. "Consumer Price Index"
    current_value: Optional[float] = None
    previous_value: Optional[float] = None
    change: Optional[float] = None       # current - previous
    unit: str = ""                       # e.g. "Index", "Percent", "Billions USD"
    frequency: str = ""                  # "Monthly", "Weekly", "Quarterly"
    date: datetime = Field(default_factory=datetime.utcnow)
    source: str = "fred"
    ingested_at: datetime = Field(default_factory=datetime.utcnow)


# ══════════════════════════════════════════════════════════════════════════════
# Node: Event / News
# ══════════════════════════════════════════════════════════════════════════════

class EventNewsNode(BaseModel):
    """
    A news headline or market event.
    Upsert key: headline_hash (MD5 of headline + date)
    """
    headline_hash: str                   # dedup key
    headline: str
    body: Optional[str] = None
    date: datetime
    source: str                          # e.g. "CryptoCompare", "CoinTelegraph"
    url: Optional[str] = None
    category: Optional[str] = None      # "Regulation", "DeFi", "Exchange", etc.
    related_assets: List[str] = []       # ["BTC", "ETH"]
    sentiment: Optional[str] = None      # "positive" | "neutral" | "negative"
    sentiment_score: Optional[float] = None  # -1.0 to 1.0
    ingested_at: datetime = Field(default_factory=datetime.utcnow)


# ══════════════════════════════════════════════════════════════════════════════
# Node: Algorithm  (written by agentic workflow, NOT the scheduled ETL)
# ══════════════════════════════════════════════════════════════════════════════

class AlgorithmNode(BaseModel):
    """
    An algorithm decision record written by the agentic workflow.
    Each write captures one activation event.
    Upsert key: (algo_name, triggered_at)
    """
    algo_name: str                       # "Mean Reversion" | "Momentum" | etc.
    optimal_market_condition: str        # "High Volatility" | "Bull Market" | etc.
    parameters: Dict[str, Any] = {}     # algo-specific config
    triggered_on_asset: Optional[str] = None   # "BTC"
    confidence_score: Optional[float] = None   # 0.0 – 1.0
    signal: Optional[str] = None        # "BUY" | "SELL" | "HOLD"
    notes: Optional[str] = None
    triggered_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = "agentic_workflow"


# ══════════════════════════════════════════════════════════════════════════════
# MongoDB collection validators (apply once at DB init)
# ══════════════════════════════════════════════════════════════════════════════

ASSET_VALIDATOR = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["ticker", "company_name", "sector"],
        "properties": {
            "ticker":       {"bsonType": "string"},
            "company_name": {"bsonType": "string"},
            "sector":       {"bsonType": "string"},
            "market_cap":   {"bsonType": ["double", "null"]},
            "price_usd":    {"bsonType": ["double", "null"]},
        },
    }
}

MACRO_VALIDATOR = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["indicator", "date"],
        "properties": {
            "indicator":     {"bsonType": "string"},
            "current_value": {"bsonType": ["double", "null"]},
        },
    }
}

ALGORITHM_VALIDATOR = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["algo_name", "optimal_market_condition"],
        "properties": {
            "algo_name":                {"bsonType": "string"},
            "optimal_market_condition": {"bsonType": "string"},
            "confidence_score": {
                "bsonType": ["double", "null"],
                "minimum": 0,
                "maximum": 1,
            },
        },
    }
}
