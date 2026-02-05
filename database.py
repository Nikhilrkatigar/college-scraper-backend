from pymongo import MongoClient
import os

MONGO_URL = os.getenv("MONGO_URL")

if not MONGO_URL:
    raise RuntimeError("MONGO_URL is not set")

client = MongoClient(MONGO_URL)

db = client.get_database()

progress_collection = db["scrape_progress"]
pagination_collection = db["scrape_pagination"]
users_collection = db["users"]
colleges_collection = db["colleges"]
contacts_collection = db["contacts"]
logs_collection = db["activity_logs"]
