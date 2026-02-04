from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from auth.routes import router as auth_router
from users.routes import router as users_router
from colleges.routes import router as colleges_router
from extractor.routes import router as extract_router
from locations.routes import router as locations_router
from dotenv import load_dotenv
load_dotenv()


app = FastAPI(title="College Placement Contact Extractor")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(colleges_router)
app.include_router(extract_router)
app.include_router(locations_router)

@app.get("/")
def root():
    return {"status": "Backend running"}
