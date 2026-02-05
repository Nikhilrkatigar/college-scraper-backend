from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

from auth.routes import router as auth_router
from users.routes import router as users_router
from colleges.routes import router as colleges_router
from extractor.routes import router as extract_router
from locations.routes import router as locations_router

load_dotenv()

app = FastAPI(title="College Placement Contact Extractor")

# ---- CORS CONFIG (FINAL & CORRECT) ----
FRONTEND_URL = os.getenv("FRONTEND_URL")

allowed_origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "https://college-scraper-frontend.vercel.app",
]

if FRONTEND_URL:
    allowed_origins.append(FRONTEND_URL)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,  # ✅ IMPORTANT FIX
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- API ROUTERS ----
app.include_router(auth_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(colleges_router, prefix="/api")
app.include_router(extract_router, prefix="/api")
app.include_router(locations_router, prefix="/api")

# ---- HEALTH CHECK ----
@app.get("/")
def root():
    return {"status": "Backend running"}
