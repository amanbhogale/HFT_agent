"""
already created collections in mongo 
designing the schema for the collections in mongo

1. validation of the data before inserting into mongo
2. As a refrence for the  collection JSON-schema validator 
"""
from __future__ import annotations
from datatime import datatime
from typing import List , Any , Dict , Optional
from pydantic import BaseModel , Field

#----------------
class AssetNode(BaseModel):
    ticker: str = Field(..., description="Ticker symbol of the asset")
    company_name: Optional[str] = Field(None, description="Company name associated with the asset")
    sector: Optional[str] = Field(None, description="Sector to which the asset belongs")
    market_cap: Optional[float] = Field(None, description="Market capitalization of the asset")
    price_inr : Optional[float] = Field(None, description="Price of the asset in INR")
    volume_24h: Optional[float] = Field(None, description="Trading volume of the asset in the last 24 hours")
    change_24h_pct: Optional[float] = Field(None, description="Price change of the asset in the last 24 hours in percentage")
    

# ===============================================
# Node MacroEconomic Indicators
# ===============================================

class MacroEconomicIndicatorNode(BaseModel):
    """
    A single macroeconomic indicator data point, such as GDP, inflation rate, or unemployment rate.
    upsetting the data in the form of a node in the graph database


    """
    indicator: str = Field(..., description="Name of the macroeconomic indicator")
    displat_name: Optional[str] = Field(None, description="Display name of the macroeconomic indicator")
    current_value: Optional[float] = Field(None, description="Current value of the macroeconomic indicator")
    previous_value: Optional[float] = Field(None, description="Previous value of the macroeconomic indicator")
    change : Optional[float] = Field(None, description="Change in the macroeconomic indicator value current value - previous value")
    unit : str = ""
    frequency: str = ""
    date: datetime = Field(default_factory=datetime.now, description="Date of the macroeconomic indicator data point")
    source: str = "fred"
    ingested_at: datetime = Field(default_factory=datetime.now, description="Timestamp when the data was ingested into the database")






