import os
from dotenv import load_dotenv

# Load .env if present
load_dotenv()

class Config:
    # DB settings
    DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
    DB_PORT = int(os.getenv("DB_PORT", 3306))
    DB_USER = os.getenv("DB_USER", "appuser")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "app_pass123")
    DB_NAME = os.getenv("DB_NAME", "testdb")

    # Anthropic Claude API
    # Support either variable name so users can set ANTHROPIC_API_KEY or CLAUDE_API_KEY in .env
    CLAUDE_API_KEY = os.getenv("ANTHROPIC_API_KEY")

