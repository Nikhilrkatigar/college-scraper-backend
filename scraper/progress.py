from fastapi import APIRouter
from database import progress_collection

router = APIRouter(prefix="/progress", tags=["Progress"])

@router.get("/")
def get_progress():
    data = progress_collection.find_one({}, {"_id": 0})
    if not data:
        return {"status": "idle", "completed": 0, "total": 0}
    return data
