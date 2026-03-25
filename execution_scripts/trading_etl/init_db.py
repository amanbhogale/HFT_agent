"""
scripts/init_db.py
  
Run this BEFORE the first pipeline 
1.creates all the collections with JSON schema validation
2.creates all teh indexes for the upsert performance
3.Insert seed Algorithm registry documents
  
Usage:
    python scripts/int_db.py
    pyton scripts/init_db.py -- drops and recreates caution data loss
  
"""
 
from __future__ import annotations
  
import argparse
import sys
import os
from pathlib import Path

from pymongo.errors import ServerSelectionTimeoutError
  
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
  
import pymongo
from pymongo import MongoClient
from pymong.errors import collectionInvalid
from schemas.mongo_schemas import (
    ASSET_VALIDATOR,
    MACRO_VALIDATOR,
    ALGORITHM_VALIDATOR,
        )
from utils.logger import get_logger

log = get_logger("init_db")

#varables

def init_db(drop: bool=False)-> None:
    mongo_uri = MongoClient(os.getenv("MONGODB_URI") , ServerSelectionTimeoutError=5000)
    db = client[os.getenv("MONGODB_DB")]
    log.info(f"Connected to MongoDB : {os.getenv("MONGODB_URI")} | DB ")
    collections = {

            }
    





