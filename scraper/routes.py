from fastapi import APIRouter
from database import colleges_collection, contacts_collection, progress_collection
from scraper.scrape_utils import scrape_html, scrape_pdf, extract_emails, extract_phones

router = APIRouter(prefix="/scrape", tags=["Scraping"])


@router.post("/run")
def run_scraping(state: str, district: str):
    colleges = list(colleges_collection.find({
        "state": state,
        "district": district
    }))

    total = len(colleges)
    completed = 0

    # reset progress
    progress_collection.delete_many({})
    progress_collection.insert_one({
        "total": total,
        "completed": 0,
        "status": "running"
    })

    for college in colleges:
        website = college.get("website")
        if not website:
            completed += 1
            progress_collection.update_one({}, {"$set": {"completed": completed}})
            continue

        if website.lower().endswith(".pdf"):
            text = scrape_pdf(website)
        else:
            text = scrape_html(website)

        emails = extract_emails(text)
        phones = extract_phones(text)

        for email in emails:
            if not contacts_collection.find_one({"email": email}):
                contacts_collection.insert_one({
                    "college_id": college["_id"],
                    "email": email,
                    "phone": None,
                    "source": website
                })

        for phone in phones:
            if not contacts_collection.find_one({"phone": phone}):
                contacts_collection.insert_one({
                    "college_id": college["_id"],
                    "email": None,
                    "phone": phone,
                    "source": website
                })

        colleges_collection.update_one(
            {"_id": college["_id"]},
            {"$set": {"completed": True}}
        )

        completed += 1
        progress_collection.update_one({}, {"$set": {"completed": completed}})

    progress_collection.update_one({}, {"$set": {"status": "done"}})

    return {"message": "Scraping completed"}
