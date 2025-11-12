# SkillSync/utils/database.py

import motor.motor_asyncio
import os
import traceback

# Get the connection string from Hugging Face Secrets
MONGO_DETAILS = os.environ.get("DB_CONNECTION_STRING")

if not MONGO_DETAILS:
    print("Warning: DB_CONNECTION_STRING secret is not set. Database will not connect.")
    client = None
    db = None
else:
    print("Connecting to MongoDB Atlas...")
    try:
        # Create the async client
        client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_DETAILS)
        
        # Get the database (it will be created if it doesn't exist)
        # This must match the name you put in your connection string
        db = client.SkillSyncDB 
        
        print("MongoDB connection established.")
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")
        traceback.print_exc()
        db = None

# We will import 'db' in other files to interact with collections
# e.g., await db["users"].insert_one(...)