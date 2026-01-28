import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from peninemate.infrastructure.db_client import get_conn
from peninemate.infrastructure.tmdb_client import get_tmdb_client
from peninemate.core_logic.qa_service import insert_credits_to_db

print("🔄 Populating credits for popular movies...")

# Top movies to populate
movie_ids = [
    597,    # Titanic
    27205,  # Inception
    155,    # The Dark Knight
    19995,  # Avatar
    603,    # The Matrix
    680,    # Pulp Fiction
    13,     # Forrest Gump
    568,    # Apollo 13
    424,    # Schindler's List
    807     # Se7en
]

tmdb_client = get_tmdb_client()
success = 0
failed = 0

for tmdb_id in movie_ids:
    try:
        print(f"⏳ Loading credits for tmdb_id={tmdb_id}...")
        credits_data = tmdb_client.get_movie_credits(tmdb_id)
        if credits_data:
            insert_credits_to_db(tmdb_id, credits_data)
            success += 1
            print(f"   ✅ Success")
        else:
            failed += 1
            print(f"   ❌ No data from TMDb")
    except Exception as e:
        failed += 1
        print(f"   ❌ Error: {e}")

print(f"\n✅ Completed: {success} success, {failed} failed")
