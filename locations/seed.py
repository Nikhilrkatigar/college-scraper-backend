from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017")
db = client["college_scraper_db"]
locations = db["locations"]

locations.delete_many({})  # reset

locations.insert_many([
    {
        "region": "South",
        "state": "Karnataka",
        "cities": ["Bengaluru", "Dharwad", "Hubli", "Belagavi", "Mysuru"]
    },
    {
        "region": "South",
        "state": "Tamil Nadu",
        "cities": ["Chennai", "Coimbatore", "Madurai", "Trichy"]
    },
    {
        "region": "West",
        "state": "Maharashtra",
        "cities": ["Mumbai", "Pune", "Nagpur", "Nashik"]
    },
    {
        "region": "North",
        "state": "Delhi",
        "cities": ["New Delhi"]
    },
    {
        "region": "East",
        "state": "West Bengal",
        "cities": ["Kolkata", "Howrah", "Durgapur"]
    }
])

print("Location data inserted successfully")
