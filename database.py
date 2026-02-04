from pymongo import MongoClient

MONGO_URL = "mongodb://localhost:27017"
client = MongoClient(MONGO_URL)

db = client["college_scraper_db"]
progress_collection = db["scrape_progress"]
pagination_collection = db["scrape_pagination"]


users_collection = db["users"]
colleges_collection = db["colleges"]
contacts_collection = db["contacts"]
logs_collection = db["activity_logs"]
