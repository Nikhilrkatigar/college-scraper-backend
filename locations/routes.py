# locations/routes.py
from fastapi import APIRouter
import json
from pathlib import Path


router = APIRouter(prefix="/locations", tags=["Locations"])

# Load India JSON once (FAST + OFFLINE)
DATA_PATH = Path(__file__).resolve().parent / "india_locations.json"

with open(DATA_PATH, "r", encoding="utf-8") as f:
    INDIA = json.load(f)

# -----------------------------
# GET REGIONS
# -----------------------------
@router.get("/regions")
def get_regions():
    return list(INDIA.keys())

# -----------------------------
# GET STATES BY REGION
# -----------------------------
@router.get("/states")
def get_states(region: str):
    return list(INDIA.get(region, {}).keys())

# -----------------------------
# GET DISTRICTS BY STATE
# -----------------------------
@router.get("/districts")
def get_districts(region: str, state: str):
    return INDIA.get(region, {}).get(state, [])
