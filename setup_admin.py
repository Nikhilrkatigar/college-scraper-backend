import os
from dotenv import load_dotenv
load_dotenv()

from database import users_collection
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# Check existing users
users = list(users_collection.find({}, {'_id': 0, 'password': 0}))
print("=== EXISTING USERS ===")
if users:
    for user in users:
        print(f"  Username: {user['username']}, Role: {user['role']}")
else:
    print("  No users found")

# Check if admin exists
admin_exists = users_collection.find_one({"username": "admin"})
if admin_exists:
    print("\n✓ Admin user already exists")
    print("  Username: admin")
else:
    print("\n✗ No admin user found")
    print("\nCreating default admin user...")
    admin_password = "admin123"
    hashed = pwd_context.hash(admin_password)
    users_collection.insert_one({
        "username": "admin",
        "password": hashed,
        "role": "admin"
    })
    print(f"✓ Admin created successfully!")
    print(f"  Username: admin")
    print(f"  Password: {admin_password}")
