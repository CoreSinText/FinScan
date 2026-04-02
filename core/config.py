"""
Application configuration and environment variables management.
"""
import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/finscan")
    # Add other configuration variables here if needed

settings = Settings()
