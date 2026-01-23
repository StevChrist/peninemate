import os
from pathlib import Path
from dotenv import load_dotenv
import psycopg2
from urllib.parse import urlparse

# Load .env dari backend/ folder (2 level ke atas)
ROOT = Path(__file__).resolve().parents[2]
load_dotenv(dotenv_path=ROOT / ".env")

def get_conn():
    """Return PostgreSQL connection - supports both DATABASE_URL and individual env vars"""
    
    # Priority 1: Use DATABASE_URL if available (for Docker)
    database_url = os.getenv("DATABASE_URL")
    
    if database_url:
        # Parse DATABASE_URL
        # Format: postgresql://user:password@host:port/dbname
        parsed = urlparse(database_url)
        return psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port or 5432,
            dbname=parsed.path.lstrip('/'),
            user=parsed.username,
            password=parsed.password,
        )
    
    # Priority 2: Use individual env vars (fallback for local dev)
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "postgres"),      # ✅ Fixed default
        port=int(os.getenv("DB_PORT", "5432")),     # ✅ Fixed default
        dbname=os.getenv("DB_NAME", "peninemate_db"),
        user=os.getenv("DB_USER", "peninemate_user"),  # ✅ Fixed default
        password=os.getenv("DB_PASSWORD", "peninemate_pass_2026"),  # ✅ Fixed default
    )