import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from peninemate.infrastructure.db_client import get_conn
from peninemate.infrastructure.tmdb_client import get_tmdb_client
from peninemate.core_logic.qa_service import insert_credits_to_db
import time

print('🔄 Populating credits for top 100 popular movies...')

# Get top 100 by popularity
conn = get_conn()
cur = conn.cursor()
cur.execute('''
    SELECT tmdb_id, title, popularity
    FROM movies
    WHERE popularity IS NOT NULL
    ORDER BY popularity DESC
    LIMIT 100
''')
movies = cur.fetchall()
cur.close()

print(f'📊 Found {len(movies)} movies to populate')

tmdb_client = get_tmdb_client()
success = 0
failed = 0

for tmdb_id, title, popularity in movies:
    try:
        print(f'⏳ {title} (tmdb_id={tmdb_id})...')
        credits_data = tmdb_client.get_movie_credits(tmdb_id)
        if credits_data:
            insert_credits_to_db(tmdb_id, credits_data)
            success += 1
            print(f'   ✅ Success')
        else:
            failed += 1
            print(f'   ❌ No data')
        time.sleep(0.25)  # Rate limit
    except Exception as e:
        failed += 1
        print(f'   ❌ Error: {e}')

print(f'\n✅ Completed: {success} success, {failed} failed')
