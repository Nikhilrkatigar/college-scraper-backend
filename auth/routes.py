from fastapi import APIRouter, HTTPException, Form, Body
from typing import Optional
from database import users_collection
from auth.auth_utils import verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login")
def login(
    username: Optional[str] = Form(None),
    password: Optional[str] = Form(None),
    body: Optional[dict] = Body(None),
):
    # ✅ Accept JSON
    if body:
        username = body.get("username")
        password = body.get("password")

    if not username or not password:
        raise HTTPException(status_code=422, detail="Username and password required")

    user = users_collection.find_one({"username": username})

    if not user or not verify_password(password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token(data={"sub": username})

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "username": username,
        "role": user.get("role"),
    }
