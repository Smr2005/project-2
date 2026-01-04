import os
from dotenv import load_dotenv

# Load .env if present
load_dotenv()

class Config:
    # DB settings
    DB_HOST = os.getenv("DB_HOST")
    DB_PORT = int(os.getenv("DB_PORT", 3306))
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASS")
    DB_NAME = os.getenv("DB_NAME")

    # Anthropic Claude API
    # Support either variable name so users can set ANTHROPIC_API_KEY or CLAUDE_API_KEY in .env
    CLAUDE_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    
    # Groq API
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")

