import os
from pathlib import Path
from dotenv import load_dotenv
import psycopg2

# Load .env dari backend/ folder (2 level ke atas)
ROOT = Path(__file__).resolve().parents[2]
load_dotenv(dotenv_path=ROOT / ".env")

def get_conn():
    """Return PostgreSQL connection with default values"""
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", "15433")),
        dbname=os.getenv("DB_NAME", "peninemate_db"),
        user=os.getenv("DB_USER", "peninemate"),
        password=os.getenv("DB_PASSWORD", "peninemate"),
    )
