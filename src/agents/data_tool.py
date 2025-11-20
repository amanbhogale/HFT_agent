"""Agentic data integration tool for financial pipelines.

This module aggregates fundamental, technical, and price data from multiple
sources (currently Finnhub) and exposes both a reusable Python API and a
command-line interface powered by argparse. The tool is intended to be used
inside LangGraph agents but can also run standalone for diagnostics or
batch data pulls.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

import pandas as pd
import requests
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from src.state import State

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s [%(name)s] %(message)s")

FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")
FINNHUB_BASE_URL = "https://finnhub.io/api/v1"

MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DB = os.getenv("MONGODB_DB", "stocks")
MONGODB_COLLECTION = os.getenv("MONGODB_COLLECTION", "data_snapshots")
MONGODB_HOST = os.getenv("MONGODB_HOST", "localhost")
MONGODB_PORT = os.getenv("MONGODB_PORT", "27017")
MONGODB_USERNAME = os.getenv("MONGODB_USERNAME")
MONGODB_PASSWORD = os.getenv("MONGODB_PASSWORD")

class DataSourceError(RuntimeError):
    """Raised when an upstream data provider responds with an error."""


def _compose_mongo_uri(
    uri: Optional[str],
    username: Optional[str],
    password: Optional[str],
    host: Optional[str],
    port: Optional[str],
    auth_db: str,
) -> Optional[str]:
    # Prioritize manual credentials (they're properly encoded)
    if username and password:
        host = host or "localhost"
        port = port or "27017"
        user = quote_plus(username)
        pwd = quote_plus(password)
        return f"mongodb://{user}:{pwd}@{host}:{port}/?authSource={auth_db}"
    # If URI is provided but no manual credentials, return as-is
    # (user should ensure it's properly encoded)
    if uri:
        return uri
    # Fallback to host-only connection
    host = host or "localhost"
    port = port or "27017"
    if host:
        return f"mongodb://{host}:{port}/"
    return None


def _require_api_key(api_key: Optional[str]) -> str:
    key = api_key or FINNHUB_API_KEY
    if not key:
        raise EnvironmentError(
            "FINNHUB_API_KEY is not set. Please export it before running the data tool."
        )
    return key


def _to_utc_timestamp(value: str) -> int:
    """Convert ISO date string (YYYY-MM-DD) to UTC epoch seconds."""
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return int(dt.timestamp())


def _request_json(url: str, params: Dict[str, Any]) -> Dict[str, Any]:
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    payload = response.json()
    if isinstance(payload, dict) and payload.get("error"):
        raise DataSourceError(payload["error"])
    return payload


def fetch_fundamental_data(symbol: str, api_key: Optional[str] = None) -> pd.DataFrame:
    """Fetch fundamental filings from Finnhub."""
    key = _require_api_key(api_key)
    url = f"{FINNHUB_BASE_URL}/stock/financials-reported"
    data = _request_json(url, {"symbol": symbol.upper(), "token": key})
    records = data.get("data", [])
    df = pd.DataFrame(records)
    if df.empty:
        logger.warning("No fundamental data returned for %s", symbol)
    return df


def _flatten_financials(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "report" not in df:
        return df

    normalized_rows: List[Dict[str, Any]] = []
    for row in df.to_dict(orient="records"):
        report = row.get("report", {})
        flattened = {k: v for k, v in row.items() if k != "report"}
        for section in ("ic", "bs", "cf"):
            entries = report.get(section, [])
            flattened.update({item["concept"]: item["value"] for item in entries})
        normalized_rows.append(flattened)
    return pd.DataFrame(normalized_rows)


def fetch_technical_indicators(
    symbol: str,
    indicator: str,
    start_ts: int,
    end_ts: int,
    resolution: str = "D",
    api_key: Optional[str] = None,
) -> pd.DataFrame:
    """Fetch technical indicator data (e.g., MACD, RSI) from Finnhub."""
    key = _require_api_key(api_key)
    url = f"{FINNHUB_BASE_URL}/indicator"
    params = {
        "symbol": symbol.upper(),
        "indicator": indicator,
        "resolution": resolution,
        "from": start_ts,
        "to": end_ts,
        "token": key,
    }
    data = _request_json(url, params)
    values = {k: v for k, v in data.items() if isinstance(v, list)}
    if not values:
        logger.warning("No technical indicator data returned for %s (%s)", symbol, indicator)
        return pd.DataFrame()

    df = pd.DataFrame(values)
    if "t" in df:
        df["timestamp"] = pd.to_datetime(df["t"], unit="s", utc=True)
        df = df.drop(columns=["t"])
    return df


def fetch_price_series(
    symbol: str,
    start_ts: int,
    end_ts: int,
    resolution: str = "D",
    api_key: Optional[str] = None,
) -> pd.DataFrame:
    """Fetch OHLCV price candles for the specified date range."""
    key = _require_api_key(api_key)
    url = f"{FINNHUB_BASE_URL}/stock/candle"
    params = {
        "symbol": symbol.upper(),
        "resolution": resolution,
        "from": start_ts,
        "to": end_ts,
        "token": key,
    }
    data = _request_json(url, params)
    if data.get("s") != "ok":
        logger.warning("Finnhub returned status %s for price data", data.get("s"))
        return pd.DataFrame()

    df = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(data.get("t", []), unit="s", utc=True),
            "open": data.get("o", []),
            "high": data.get("h", []),
            "low": data.get("l", []),
            "close": data.get("c", []),
            "volume": data.get("v", []),
        }
    )
    return df


@dataclass
class DataBundle:
    symbol: str
    fundamentals: pd.DataFrame
    technicals: pd.DataFrame
    prices: pd.DataFrame
    indicator: str
    resolution: str
    start_ts: int
    end_ts: int

    def as_payload(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "fundamentals": {
                "source": "finnhub",
                "records": self.fundamentals.to_dict(orient="records"),
            },
            "technicals": {
                "source": "finnhub",
                "indicator": self.indicator,
                "resolution": self.resolution,
                "records": self.technicals.to_dict(orient="records"),
            },
            "prices": {
                "source": "finnhub",
                "resolution": self.resolution,
                "records": self.prices.to_dict(orient="records"),
            },
            "time_range": {
                "start_ts": self.start_ts,
                "end_ts": self.end_ts,
            },
        }


class DataIntegrationTool:
    """High-level orchestrator for the agentic data pipeline."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        mongo_uri: Optional[str] = None,
        mongo_db: Optional[str] = None,
        mongo_collection: Optional[str] = None,
        mongo_host: Optional[str] = None,
        mongo_port: Optional[str] = None,
        mongo_username: Optional[str] = None,
        mongo_password: Optional[str] = None,
    ):
        self.api_key = api_key or FINNHUB_API_KEY
        self.mongo_uri = mongo_uri or MONGODB_URI
        self.mongo_db = mongo_db or MONGODB_DB
        self.mongo_collection = mongo_collection or MONGODB_COLLECTION
        self.mongo_host = mongo_host or MONGODB_HOST
        self.mongo_port = mongo_port or MONGODB_PORT
        self.mongo_username = mongo_username or MONGODB_USERNAME
        self.mongo_password = mongo_password or MONGODB_PASSWORD

    def run(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        indicator: str = "macd",
        resolution: str = "D",
    ) -> DataBundle:
        start_ts = _to_utc_timestamp(start_date)
        end_ts = _to_utc_timestamp(end_date)
        fundamentals = _flatten_financials(fetch_fundamental_data(symbol, self.api_key))
        try:
            technicals = fetch_technical_indicators(
                symbol, indicator, start_ts, end_ts, resolution, self.api_key
            )
        except (requests.HTTPError, DataSourceError, ValueError) as exc:
            logger.warning(
                "Skipping technical indicators for %s (%s): %s",
                symbol,
                indicator,
                exc,
            )
            technicals = pd.DataFrame()
        try:
            prices = fetch_price_series(symbol, start_ts, end_ts, resolution, self.api_key)
        except (requests.HTTPError, DataSourceError, ValueError) as exc:
            logger.warning(
                "Skipping price series for %s (%s): %s",
                symbol,
                resolution,
                exc,
            )
            prices = pd.DataFrame()
        return DataBundle(
            symbol=symbol.upper(),
            fundamentals=fundamentals,
            technicals=technicals,
            prices=prices,
            indicator=indicator,
            resolution=resolution,
            start_ts=start_ts,
            end_ts=end_ts,
        )

    def store_payload(
        self,
        payload: Dict[str, Any],
        mongo_uri: Optional[str] = None,
        mongo_db: Optional[str] = None,
        mongo_collection: Optional[str] = None,
        mongo_host: Optional[str] = None,
        mongo_port: Optional[str] = None,
        mongo_username: Optional[str] = None,
        mongo_password: Optional[str] = None,
    ) -> str:
        """Persist the aggregated payload into MongoDB."""
        uri = _compose_mongo_uri(
            uri=mongo_uri or self.mongo_uri,
            username=mongo_username or self.mongo_username,
            password=mongo_password or self.mongo_password,
            host=mongo_host or self.mongo_host,
            port=mongo_port or self.mongo_port,
            auth_db=mongo_db or self.mongo_db or MONGODB_DB,
        )
        if not uri:
            raise EnvironmentError(
                "MongoDB storage requested but no URI provided. "
                "Set MONGODB_URI or pass --mongo-uri."
            )
        db_name = mongo_db or self.mongo_db or "stocks"
        collection_name = mongo_collection or self.mongo_collection or "data_snapshots"

        document = dict(payload)
        document["ingested_at"] = datetime.now(timezone.utc).isoformat()

        try:
            with MongoClient(uri) as client:
                collection = client[db_name][collection_name]
                result = collection.insert_one(document)
                logger.info(
                    "Stored payload for %s in %s.%s (id=%s)",
                    payload.get("symbol"),
                    db_name,
                    collection_name,
                    result.inserted_id,
                )
                return str(result.inserted_id)
        except PyMongoError as exc:
            raise RuntimeError(f"Failed to store payload in MongoDB: {exc}") from exc


def update_state_with_data(state: State, payload: Dict[str, Any]) -> State:
    """Merge the aggregated payload into the LangGraph agent state."""
    next_state: State = dict(state)
    next_state["symbol"] = payload.get("symbol")
    next_state["fundamental_data"] = payload.get("fundamentals")
    next_state["technical_data"] = payload.get("technicals")
    next_state["price_data"] = payload.get("prices")

    summary = f"Loaded fundamentals ({len(payload['fundamentals']['records'])} records), "
    summary += f"technicals ({len(payload['technicals']['records'])}), "
    summary += f"prices ({len(payload['prices']['records'])})."
    next_state.setdefault("messages", []).append(summary)
    return next_state


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Pull fundamental, technical, and price data for a ticker."
    )
    parser.add_argument("--symbol", required=True, help="Ticker symbol, e.g., AAPL")
    parser.add_argument(
        "--start-date",
        required=True,
        help="Start date (YYYY-MM-DD, assumed UTC).",
    )
    parser.add_argument(
        "--end-date",
        required=True,
        help="End date (YYYY-MM-DD, assumed UTC).",
    )
    parser.add_argument(
        "--indicator",
        default="macd",
        help="Technical indicator to request (default: macd).",
    )
    parser.add_argument(
        "--resolution",
        default="D",
        choices=["1", "5", "15", "30", "60", "D", "W", "M"],
        help="Candle resolution for technical/price data.",
    )
    parser.add_argument(
        "--output",
        choices=["json", "pretty"],
        default="json",
        help="Output format for CLI invocations.",
    )
    parser.add_argument(
        "--store",
        action="store_true",
        help="Persist the aggregated payload in MongoDB.",
    )
    parser.add_argument(
        "--mongo-uri",
        help="MongoDB connection string (defaults to MONGODB_URI env).",
    )
    parser.add_argument(
        "--mongo-db",
        help=f"MongoDB database name (default: {MONGODB_DB}).",
    )
    parser.add_argument(
        "--mongo-collection",
        help=f"MongoDB collection name (default: {MONGODB_COLLECTION}).",
    )
    parser.add_argument(
        "--mongo-host",
        help=f"MongoDB host (default: {MONGODB_HOST}).",
    )
    parser.add_argument(
        "--mongo-port",
        help=f"MongoDB port (default: {MONGODB_PORT}).",
    )
    parser.add_argument(
        "--mongo-username",
        help="MongoDB username (will be encoded automatically).",
    )
    parser.add_argument(
        "--mongo-password",
        help="MongoDB password (will be encoded automatically).",
    )
    return parser


def run_cli() -> None:
    parser = build_parser()
    args = parser.parse_args()
    tool = DataIntegrationTool(
        mongo_uri=args.mongo_uri,
        mongo_db=args.mongo_db,
        mongo_collection=args.mongo_collection,
        mongo_host=args.mongo_host,
        mongo_port=args.mongo_port,
        mongo_username=args.mongo_username,
        mongo_password=args.mongo_password,
    )
    bundle = tool.run(
        symbol=args.symbol,
        start_date=args.start_date,
        end_date=args.end_date,
        indicator=args.indicator,
        resolution=args.resolution,
    )
    payload = bundle.as_payload()
    if args.output == "pretty":
        print(json.dumps(payload, indent=2, default=str))
    else:
        print(json.dumps(payload, default=str))

    if args.store or any([args.mongo_uri, args.mongo_db, args.mongo_collection]):
        inserted_id = tool.store_payload(
            payload,
            mongo_uri=args.mongo_uri,
            mongo_db=args.mongo_db,
            mongo_collection=args.mongo_collection,
            mongo_host=args.mongo_host,
            mongo_port=args.mongo_port,
            mongo_username=args.mongo_username,
            mongo_password=args.mongo_password,
        )
        print(f"Stored document id: {inserted_id}")


if __name__ == "__main__":
    run_cli()
