import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()

async def init_db():
    uri = os.getenv("MONGO_URI")
    db_name = os.getenv("MONGO_DB_NAME")
    client = AsyncIOMotorClient(uri)
    db = client[db_name]
    
    print(f"Initializing collections in {db_name}...")
    try:
        # Create collections if they don't exist
        collections = await db.list_collection_names()
        if "users" not in collections:
            await db.create_collection("users")
            print("Created 'users' collection.")
        if "vault" not in collections:
            await db.create_collection("vault")
            print("Created 'vault' collection.")
            
        # Create index on email
        await db.users.create_index("email", unique=True)
        print("Ensured unique index on users.email")
        
        print("Database initialization complete.")
    except Exception as e:
        print(f"Initialization failed: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(init_db())
