# peninemate/qa_db.py (FIX - Add typing imports at top)
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from typing import List, Dict, Optional  # ← ADD THIS LINE!
from peninemate.infrastructure.db_client import get_conn

def search_movies_by_title(title: str, limit: int = 5) -> List[Dict]:
    """Search movies by title (keyword search)."""
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT tmdb_id, title, year, overview, popularity
        FROM movies
        WHERE title ILIKE %s
        ORDER BY popularity DESC
        LIMIT %s
    """, (f"%{title}%", limit))
    
    results = []
    for row in cur.fetchall():
        results.append({
            "tmdb_id": row[0],
            "title": row[1],
            "year": row[2],
            "overview": row[3],
            "popularity": row[4]
        })
    
    conn.close()
    return results

def get_movie_by_tmdb_id(tmdb_id: int) -> Optional[Dict]:
    """Get movie by TMDb ID."""
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT tmdb_id, title, year, overview, genres_csv,
               box_office_worldwide, box_office_domestic, box_office_foreign,
               popularity, data_source
        FROM movies
        WHERE tmdb_id = %s
    """, (tmdb_id,))
    
    row = cur.fetchone()
    conn.close()
    
    if not row:
        return None
    
    return {
        "tmdb_id": row[0],
        "title": row[1],
        "year": row[2],
        "overview": row[3],
        "genres_csv": row[4],
        "box_office_worldwide": row[5],
        "box_office_domestic": row[6],
        "box_office_foreign": row[7],
        "popularity": row[8],
        "data_source": row[9]
    }

def search_movies_by_director(director_name: str, limit: int = 10):
    """
    Search movies by director name
    
    Args:
        director_name: Director's name
        limit: Max results
        
    Returns:
        List of movie dicts
    """
    conn = get_conn()
    cur = conn.cursor()
    
    try:
        # FIXED: Use correct column names from schema
        # credits.movie_tmdb_id (not movie_id)
        # credits.person_tmdb_person_id (links to people.tmdb_person_id)
        # movies.year (not release_year)
        query = """
            SELECT DISTINCT 
                m.tmdb_id, 
                m.title, 
                m.year,
                m.overview,
                m.popularity
            FROM movies m
            JOIN credits c ON m.tmdb_id = c.movie_tmdb_id
            JOIN people p ON c.person_tmdb_person_id = p.tmdb_person_id
            WHERE p.name ILIKE %s 
                AND c.credit_type = 'crew' 
                AND c.job = 'Director'
            ORDER BY m.popularity DESC NULLS LAST
            LIMIT %s
        """
        
        cur.execute(query, (f"%{director_name}%", limit))
        
        results = []
        for row in cur.fetchall():
            results.append({
                'tmdb_id': row[0],
                'title': row[1],
                'year': row[2],
                'overview': row[3],
                'popularity': row[4],
                'source': 'director_search'
            })
        
        return results
        
    finally:
        cur.close()
        conn.close()


def search_movies_by_actor(actor_name: str, limit: int = 10):
    """
    Search movies by actor name
    
    Args:
        actor_name: Actor's name
        limit: Max results
        
    Returns:
        List of movie dicts
    """
    conn = get_conn()
    cur = conn.cursor()
    
    try:
        # FIXED: Use correct column names
        query = """
            SELECT DISTINCT 
                m.tmdb_id, 
                m.title, 
                m.year,
                m.overview,
                m.popularity
            FROM movies m
            JOIN credits c ON m.tmdb_id = c.movie_tmdb_id
            JOIN people p ON c.person_tmdb_person_id = p.tmdb_person_id
            WHERE p.name ILIKE %s 
                AND c.credit_type = 'cast'
            ORDER BY m.popularity DESC NULLS LAST
            LIMIT %s
        """
        
        cur.execute(query, (f"%{actor_name}%", limit))
        
        results = []
        for row in cur.fetchall():
            results.append({
                'tmdb_id': row[0],
                'title': row[1],
                'year': row[2],
                'overview': row[3],
                'popularity': row[4],
                'source': 'actor_search'
            })
        
        return results
        
    finally:
        cur.close()
        conn.close()

def get_credits_for_movie(tmdb_id: int) -> List[Dict]:
    """Get credits (cast + crew) for a movie."""
    conn = get_conn()
    cur = conn.cursor()
    
    # Check if credits table exists
    cur.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_name = 'credits'
    """)
    
    if not cur.fetchone():
        conn.close()
        return []
    
    cur.execute("""
        SELECT c.credit_type, p.name, c.character_name, c.job, c.cast_order
        FROM credits c
        JOIN people p ON c.person_tmdb_person_id = p.tmdb_person_id
        WHERE c.movie_tmdb_id = %s
        ORDER BY c.cast_order
    """, (tmdb_id,))
    
    results = []
    for row in cur.fetchall():
        results.append({
            "credit_type": row[0],
            "name": row[1],
            "character_name": row[2],
            "job": row[3],
            "cast_order": row[4]
        })
    
    conn.close()
    return results

# Test
if __name__ == "__main__":
    print("=" * 60)
    print("TEST 1: Search Movies by Title")
    print("=" * 60)
    results = search_movies_by_title("Inception")
    for r in results:
        print(f"  • {r['title']} ({r['year']}) - TMDb ID: {r['tmdb_id']}")
    
    print("\n" + "=" * 60)
    print("TEST 2: Get Movie by TMDb ID")
    print("=" * 60)
    if results:
        movie = get_movie_by_tmdb_id(results[0]['tmdb_id'])
        if movie:
            print(f"  Title: {movie['title']}")
            print(f"  Year: {movie['year']}")
            print(f"  Box Office: ${movie.get('box_office_worldwide', 0):,}")
