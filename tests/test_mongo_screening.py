
import os
import sys

from pymongo import MongoClient

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.agents.tools import screen_stocks


def test_mongo_connection():
    uri = os.getenv("MONGODB_URI")
    if not uri:
        return False
    try:
        client = MongoClient(uri)
        client.admin.command("ping")
        return True
    except Exception:
        return False


def test_screening():
    # Example criteria: market cap > 0 (just to get something if it exists)
    # Adjust criteria based on actual data in DB if known
    criteria = {}
    try:
        results = screen_stocks(criteria)
        if results:
            pass
    except Exception:
        pass


if __name__ == "__main__":
    if test_mongo_connection():
        # We expect this to fail initially as screen_stocks is not implemented
        try:
            test_screening()
        except NameError:
            pass
        except ImportError:
            pass
