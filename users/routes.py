from fastapi import APIRouter, Depends, HTTPException
from database import users_collection
from auth.auth_utils import get_current_user, hash_password
from pydantic import BaseModel
from bson import ObjectId

router = APIRouter(prefix="/users", tags=["Users"])


class UserCreate(BaseModel):
    username: str
    password: str
    role: str  # admin or user


@router.get("/me")
def get_me(current_user=Depends(get_current_user)):
    return {
        "username": current_user["username"],
        "role": current_user["role"]
    }


@router.get("/")
def list_users(current_user=Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Access denied")

    users = list(users_collection.find({}, {"_id": 0, "password": 0}))
    return users


@router.post("/add")
def add_user(user: UserCreate, current_user=Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Access denied")

    if users_collection.find_one({"username": user.username}):
        raise HTTPException(status_code=400, detail="User already exists")

    users_collection.insert_one({
        "username": user.username,
        "password": hash_password(user.password),
        "role": user.role
    })

    return {"message": "User created successfully"}

@router.delete("/delete/{username}")
def delete_user(username: str, current_user=Depends(get_current_user)):
    # Only admin can delete users
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Access denied")

    # Prevent admin deleting himself
    if current_user["username"] == username:
        raise HTTPException(status_code=400, detail="Admin cannot delete self")

    result = users_collection.delete_one({"username": username})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")

    return {"message": "User deleted successfully"}

