import asyncio
import aiomysql
import os
from dotenv import load_dotenv

load_dotenv()

async def test():
    host = os.getenv("DB_HOST", "127.0.0.1")
    port = int(os.getenv("DB_PORT", 3306))
    user = os.getenv("DB_USER", "appuser")
    password = os.getenv("DB_PASS", "app_pass123")
    database = os.getenv("DB_NAME", "testdb")
    
    print(f"Attempting to connect to {host}:{port} as {user}...")
    try:
        conn = await asyncio.wait_for(
            aiomysql.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                db=database
            ),
            timeout=5.0
        )
        print("Connection successful!")
        conn.close()
    except asyncio.TimeoutError:
        print("Connection timed out after 5 seconds.")
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test())
