

from pymongo import MongoClient
#thinking of using pyspark 
from pyspark.sql import SparkSession
from pyspark.sql import Row
import os
import pandas as pd
import collections
import json
import bson
data = bson


# MongoDB connection parameters
MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DB = os.getenv("MONGODB_DB", "stocks")
MONGODB_COLLECTION = os.getenv("MONGODB_COLLECTION", "data_snapshots")
MONGODB_HOST = os.getenv("MONGODB_HOST", "localhost")
MONGODB_PORT = os.getenv("MONGODB_PORT", "27017")
MONGODB_USERNAME = os.getenv("MONGODB_USERNAME")
MONGODB_PASSWORD = os.getenv("MONGODB_PASSWORD")





# Construct the connection URI properly
if MONGODB_USERNAME and MONGODB_PASSWORD:
    mongo_conn_uri = f"mongodb://{MONGODB_USERNAME}:{MONGODB_PASSWORD}@{MONGODB_HOST}:{MONGODB_PORT}/?authSource={MONGODB_DB}"
else:
    mongo_conn_uri = MONGODB_URI or f"mongodb://{MONGODB_HOST}:{MONGODB_PORT}/?authSource={MONGODB_DB}"
print("Using MONGODB_URI from environment variables.")
# Connect to MongoDB
client = MongoClient(mongo_conn_uri)
db = client[MONGODB_DB]
collection = db[MONGODB_COLLECTION]
data = list(collection.find())
print(f"Fetched {len(data)} records from MongoDB.")



#creare inmemory spark dataframe cluster 

#why there should be input and output uri
#provide ans
# The input and output URIs are used to specify the source and destination for data when reading from or writing to MongoDB using Spark.
# the source is data collection in mongodb
# so i donot need output uri
#


# creating dataframe using pandas 
# from json format 


df = pd.DataFrame(data)
print("DataFrame created using pandas.")

# taking id firstly we will make pipeline for fundemental data 
fundamental_df = df[['symbol', 'fundamentals']].copy()
# make attributes colums from fundamentals data 
fundamental_expanded = pd.json_normalize(fundamental_df['fundamentals'])
print(fundamental_expanded.columns)

fundamental_final_df = pd.concat([fundamental_df[['symbol']], fundamental_expanded], axis=1)
print("Fundamental DataFrame expanded.")
print(fundamental_final_df.head())

# if we usy only pymongo to manipulate data for EDA 
# we can use aggregation pipeline to unwind fundamentals data
# but for now we will use pandas and later we can optimize it using aggregation pipeline
#use json module to parse fundamentals data and aggrigate multidemensional data into flat table with columns 
def parse_fundamentals(data):
    try:
        if isinstance(data , (str ,  bytes)):
            data = json.loads(data)
        elif isinstance(data , bson.Binary):
            data = bson.loads(data)
        elif isinstance(data , dict):
            data = data
        else:
            raise ValueError("Unsupported data type for fundamentals")
    except Exception as e:
        print(f"Error parsing fundamentals data: {e}")
        return {}
parse_fundamentals(data[0]['fundamentals'])

print(parse_fundamentals(data[0]['fundamentals']))

# Mocking find method for demonstration
# if the data is stored in mongo db collection then it will be in bson formay 

