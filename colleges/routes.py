from fastapi import APIRouter
from database import colleges_collection, contacts_collection
from bson import ObjectId

import pandas as pd
from fastapi.responses import FileResponse
import uuid

router = APIRouter(prefix="/colleges", tags=["Colleges"])


# ----------------------------
# GET ALL COLLEGES (MAIN API)
# ----------------------------
# colleges/routes.py
@router.get("")
def get_colleges(
    state: str = None,
    city: str = None,
    type: str = None,
    skip: int = 0,
    limit: int = 50
):
    query = {}

    if state:
        query["state"] = state
    if city:
        query["city"] = city
    if type and type.lower() != "all":
        query["type"] = type

    colleges = list(colleges_collection.find(query).skip(skip).limit(limit))

    for c in colleges:
        c["_id"] = str(c["_id"])

    return colleges

@router.put("/update/{college_id}")
def update_college(college_id: str, payload: dict):
    colleges_collection.update_one(
        {"_id": ObjectId(college_id)},
        {"$set": payload}
    )
    return {"message": "College updated"}



# ----------------------------
# FILTER METADATA
# ----------------------------
@router.get("/filters")
def get_filters():
    districts = colleges_collection.distinct("city")
    extracted_by = colleges_collection.distinct("done_by")
    states = colleges_collection.distinct("state")

    return {
        "districts": sorted([d for d in districts if d]),
        "extracted_by": sorted([u for u in extracted_by if u]),
        "states": sorted([s for s in states if s])
    }


# ----------------------------
# DELETE COLLEGE
# ----------------------------
@router.delete("/delete/{college_id}")
def delete_college(college_id: str):
    colleges_collection.delete_one({"_id": ObjectId(college_id)})
    contacts_collection.delete_many({"college_id": ObjectId(college_id)})
    return {"message": "College deleted permanently"}


# ----------------------------
# DELETE ALL COLLEGES
# ----------------------------
@router.delete("/delete-all")
def delete_all_colleges():
    colleges_collection.delete_many({})
    contacts_collection.delete_many({})
    return {"message": "All colleges deleted permanently"}


# ----------------------------
# TOGGLE COMPLETED
# ----------------------------
@router.put("/completed/{college_id}")
def mark_completed(college_id: str, completed: bool):
    colleges_collection.update_one(
        {"_id": ObjectId(college_id)},
        {"$set": {"completed": completed}}
    )
    return {"message": "Status updated"}


# ----------------------------
# EXPORT TO EXCEL
# ----------------------------
@router.get("/export/excel")
def export_excel():
    colleges = list(colleges_collection.find({}))

    if not colleges:
        return {"message": "No data to export"}

    rows = []

    for c in colleges:
        rows.append({
            "College Name": c.get("college_name", ""),
            "Email": c.get("email", ""),
            "Mobile": c.get("mobile", ""),
            "City": c.get("city", ""),
            "State": c.get("state", ""),
            "Region": c.get("region", ""),
            "Type": c.get("type", ""),
            "Website": c.get("website", ""),
            "Extracted By": c.get("done_by", ""),
            "Completed": c.get("completed", False),
            "College Visited": c.get("college_visited", ""),
            "College Visited By": c.get("college_visited_by", "")
        })

    df = pd.DataFrame(rows)
    filename = f"college_database_{uuid.uuid4().hex}.xlsx"
    df.to_excel(filename, index=False)

    return FileResponse(
        path=filename,
        filename="college_database.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
