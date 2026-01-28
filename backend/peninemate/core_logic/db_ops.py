"""Database operations for movie data"""

import logging
from peninemate.infrastructure.db_client import get_conn

logger = logging.getLogger(__name__)


def save_movie_to_db(tmdb_id: int) -> bool:
    """
    Save movie from TMDb to PostgreSQL database with credits
    
    Args:
        tmdb_id: TMDb movie ID
    
    Returns:
        True if saved successfully, False otherwise
    """
    from peninemate.infrastructure.tmdb_client import get_tmdb_client
    
    try:
        # Get movie details from TMDb
        tmdb = get_tmdb_client()
        movie = tmdb.get_movie_details(tmdb_id)
        credits = tmdb.get_movie_credits(tmdb_id)
        
        if not movie:
            logger.warning(f"⚠️ Movie {tmdb_id} not found in TMDb")
            return False
        
        # Extract data
        title = movie.get('title', 'Unknown')
        release_date = movie.get('release_date', None)
        overview = movie.get('overview', '')
        popularity = movie.get('popularity', 0.0)
        vote_average = movie.get('vote_average', 0.0)
        vote_count = movie.get('vote_count', 0)
        runtime = movie.get('runtime', 0)
        poster_path = movie.get('poster_path')
        backdrop_path = movie.get('backdrop_path')
        
        # Extract year
        year = None
        if release_date:
            try:
                year = int(release_date[:4])
            except:
                pass
        
        # Extract genres as CSV string (for compatibility)
        genres_json = movie.get('genres', [])
        genres_csv = ', '.join([g['name'] for g in genres_json]) if genres_json else ''
        
        # Save to database
        conn = get_conn()
        cursor = conn.cursor()
        
        # Check if movie already exists
        cursor.execute("SELECT tmdb_id FROM movies WHERE tmdb_id = %s", (tmdb_id,))
        exists = cursor.fetchone()
        
        if exists:
            logger.info(f"ℹ️ Movie {tmdb_id} already exists in DB")
            cursor.close()
            return True
        
        # Insert movie
        insert_query = """
            INSERT INTO movies (
                tmdb_id, title, release_date, overview, 
                popularity, vote_average, vote_count, 
                year, genres_csv, runtime,
                poster_path, backdrop_path
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (tmdb_id) DO NOTHING
        """
        
        cursor.execute(insert_query, (
            tmdb_id, title, release_date, overview,
            popularity, vote_average, vote_count,
            year, genres_csv, runtime,
            poster_path, backdrop_path
        ))
        
        # Save credits (directors and cast)
        if credits:
            # Save cast
            if 'cast' in credits:
                for i, cast_member in enumerate(credits['cast'][:20]):  # Top 20 cast
                    person_id = cast_member.get('id')
                    person_name = cast_member.get('name')
                    character = cast_member.get('character', '')
                    
                    if person_id and person_name:
                        # Insert person if not exists
                        cursor.execute("""
                            INSERT INTO people (tmdb_person_id, name)
                            VALUES (%s, %s)
                            ON CONFLICT (tmdb_person_id) DO NOTHING
                        """, (person_id, person_name))
                        
                        # Insert credit
                        cursor.execute("""
                            INSERT INTO credits (
                                movie_tmdb_id, person_tmdb_person_id,
                                credit_type, character_name, cast_order
                            ) VALUES (%s, %s, %s, %s, %s)
                            ON CONFLICT DO NOTHING
                        """, (tmdb_id, person_id, 'cast', character, i))
            
            # Save crew (directors)
            if 'crew' in credits:
                for crew_member in credits['crew']:
                    if crew_member.get('job') == 'Director':
                        person_id = crew_member.get('id')
                        person_name = crew_member.get('name')
                        
                        if person_id and person_name:
                            # Insert person if not exists
                            cursor.execute("""
                                INSERT INTO people (tmdb_person_id, name)
                                VALUES (%s, %s)
                                ON CONFLICT (tmdb_person_id) DO NOTHING
                            """, (person_id, person_name))
                            
                            # Insert credit
                            cursor.execute("""
                                INSERT INTO credits (
                                    movie_tmdb_id, person_tmdb_person_id,
                                    credit_type, job
                                ) VALUES (%s, %s, %s, %s)
                                ON CONFLICT DO NOTHING
                            """, (tmdb_id, person_id, 'crew', 'Director'))
        
        conn.commit()
        cursor.close()
        
        logger.info(f"✅ Movie {title} ({year}) saved to DB successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error saving movie to DB: {e}", exc_info=True)
        return False


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
