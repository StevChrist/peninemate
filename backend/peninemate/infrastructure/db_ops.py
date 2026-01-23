# peninemate/db_ops.py (UPDATED - Use correct column names)
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent))

from peninemate.infrastructure.db_client import get_conn


def upsert_movie(movie_data: dict):
    """
    Insert or update a movie in the database.
    
    Args:
        movie_data: Dict with movie fields
    """
    conn = get_conn()
    cur = conn.cursor()
    
    try:
        # Extract TMDb ID (CRITICAL!)
        tmdb_id = movie_data.get('id') or movie_data.get('tmdb_id')
        
        if not tmdb_id:
            raise ValueError(f"Missing tmdb_id in movie_data: {movie_data.get('title', 'Unknown')}")
        
        # Build INSERT with ON CONFLICT UPDATE
        cur.execute("""
            INSERT INTO movies (
                tmdb_id, title, original_title, release_date, year,
                overview, genres_json, popularity, vote_average, vote_count,
                poster_path, backdrop_path
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (tmdb_id) DO UPDATE SET
                title = EXCLUDED.title,
                original_title = EXCLUDED.original_title,
                release_date = EXCLUDED.release_date,
                year = EXCLUDED.year,
                overview = EXCLUDED.overview,
                genres_json = EXCLUDED.genres_json,
                popularity = EXCLUDED.popularity,
                vote_average = EXCLUDED.vote_average,
                vote_count = EXCLUDED.vote_count,
                poster_path = EXCLUDED.poster_path,
                backdrop_path = EXCLUDED.backdrop_path
            RETURNING id
        """, (
            tmdb_id,
            movie_data.get('title'),
            movie_data.get('original_title'),
            movie_data.get('release_date'),
            movie_data.get('release_date', '')[:4] if movie_data.get('release_date') else None,
            movie_data.get('overview'),
            movie_data.get('genres'),  # Already JSON from TMDb
            movie_data.get('popularity'),
            movie_data.get('vote_average'),
            movie_data.get('vote_count'),
            movie_data.get('poster_path'),
            movie_data.get('backdrop_path')
        ))
        
        movie_id = cur.fetchone()[0]
        conn.commit()
        
        return movie_id
        
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()


def get_movie_by_tmdb_id(tmdb_id: int):
    """Get movie by TMDb ID"""
    conn = get_conn()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            SELECT tmdb_id, title, year, overview, popularity
            FROM movies 
            WHERE tmdb_id = %s
        """, (tmdb_id,))
        
        row = cur.fetchone()
        if row:
            return {
                'tmdb_id': row[0],
                'title': row[1],
                'year': row[2],
                'overview': row[3],
                'popularity': row[4]
            }
        return None
        
    finally:
        cur.close()
        conn.close()

# Test
if __name__ == "__main__":
    print("Testing db_ops...")
    
    test_movie = {
        'tmdb_id': 27205,
        'title': 'Inception',
        'year': 2010,
        'overview': 'A thief who steals corporate secrets...',
        'genres_csv': 'Action,Science Fiction,Thriller',
        'box_office_worldwide': 828258695,
        'box_office_domestic': 292576195,
        'box_office_foreign': 535682500,
        'popularity_score': 82.5,
        'data_source': 'test'
    }
    
    try:
        upsert_movie(test_movie)
        print("✅ Movie upsert successful!")
    except Exception as e:
        print(f"❌ Movie upsert failed: {e}")
