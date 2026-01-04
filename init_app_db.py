import asyncio
import aiomysql
import os
from dotenv import load_dotenv

load_dotenv()

async def init_app_db():
    # Use existing env vars or defaults
    host = os.getenv("DB_HOST")
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASS")
    database = os.getenv("DB_NAME")
    port = int(os.getenv("DB_PORT", 3306))

    print(f"Connecting to {host}:{port} to initialize app tables...")
    
    conn = await aiomysql.connect(
        host=host, port=port,
        user=user, password=password,
        db=database
    )

    async with conn.cursor() as cur:
        # Create Users table
        await cur.execute("""
            CREATE TABLE IF NOT EXISTS qv_users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                hashed_password VARCHAR(255) NOT NULL,
                full_name VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create Vault items table (per user)
        await cur.execute("""
            CREATE TABLE IF NOT EXISTS qv_vault (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                connection_name VARCHAR(100) NOT NULL,
                encrypted_config TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES qv_users(id) ON DELETE CASCADE
            )
        """)
        
    await conn.commit()
    conn.close()
    print("Application tables initialized successfully.")

if __name__ == "__main__":
    asyncio.run(init_app_db())
