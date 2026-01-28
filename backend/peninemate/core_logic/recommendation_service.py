"""
Movie recommendation service based on user preferences
DB-first approach with TMDb fallback + auto-save
"""
import random
import logging
from typing import List, Dict, Optional
from peninemate.infrastructure.db_client import get_conn
from peninemate.infrastructure.tmdb_client import get_tmdb_client

logger = logging.getLogger(__name__)


def recommend_movie(
    genres: List[str] = None,
    mood: List[str] = None,
    theme: List[str] = None,
    storyline: List[str] = None,
    year: List[str] = None,
    duration: List[str] = None,
    duration_comparison: str = "exact",
    exclude: List[str] = None
) -> Optional[Dict]:
    """
    Recommend a movie based on user preferences
    Flow: DB → TMDb API (with auto-save) → Empty Result
    
    Args:
        genres: List of preferred genres
        mood: List of moods (not used for DB query)
        theme: List of themes (not used for DB query)
        storyline: List of storyline preferences (not used for DB query)
        year: List of preferred years
        duration: List of duration values in minutes (not supported in DB)
        duration_comparison: "over", "less", or "exact" (not supported in DB)
        exclude: List of movie titles to exclude
    
    Returns:
        Dict with movie information or None if no match found
    """
    logger.info(f"🎯 Recommendation request: genres={genres}, year={year}")
    
    # Step 1: Try DB first
    db_result = _search_from_db(genres, year, exclude)
    if db_result:
        logger.info(f"✅ DB result: {db_result['title']}")
        return db_result
    
    # Step 2: If DB empty, try TMDb API + auto-save
    logger.info("📡 Trying TMDb API fallback with auto-save...")
    tmdb_result = _search_from_tmdb_with_save(genres, year)
    if tmdb_result:
        logger.info(f"✅ TMDb result (saved): {tmdb_result['title']}")
        return tmdb_result
    
    # Step 3: No results found
    logger.warning("⚠️ No recommendation found")
    return None


def _search_from_db(
    genres: List[str] = None,
    year: List[str] = None,
    exclude: List[str] = None
) -> Optional[Dict]:
    """Search movies from local database"""
    conn = get_conn()
    cursor = conn.cursor()
    
    try:
        # Base query - only columns that DEFINITELY exist
        query = """
            SELECT DISTINCT
                m.tmdb_id,
                m.title,
                m.release_date,
                m.overview,
                m.popularity,
                m.vote_average,
                m.genres_csv,
                m.year
            FROM movies m
            WHERE m.vote_average > 0
        """
        params = []
        
        # Filter by genres (from genres_csv)
        if genres:
            genre_conditions = []
            for genre in genres:
                genre_conditions.append("m.genres_csv ILIKE %s")
                params.append(f"%{genre}%")
            query += f" AND ({' OR '.join(genre_conditions)})"
        
        # Filter by year
        if year:
            year_values = []
            for y in year:
                try:
                    year_values.append(int(y))
                except ValueError:
                    pass
            if year_values:
                query += " AND m.year = ANY(%s)"
                params.append(year_values)
        
        # Exclude movies
        if exclude:
            placeholders = ','.join(['%s'] * len(exclude))
            query += f" AND m.title NOT IN ({placeholders})"
            params.extend(exclude)
        
        # Order by popularity and rating
        query += " ORDER BY m.popularity DESC, m.vote_average DESC LIMIT 20"
        
        logger.info(f"🔍 DB Query: {query[:200]}... with {len(params)} params")
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        if not results:
            logger.info("📭 No results from DB")
            cursor.close()
            return None
        
        logger.info(f"📊 Found {len(results)} movies in DB")
        
        # Pick a random movie from top results
        movie_data = random.choice(results)
        
        # Get cast for the movie
        cast_query = """
            SELECT DISTINCT p.name
            FROM credits c
            JOIN people p ON c.person_tmdb_person_id = p.tmdb_person_id
            WHERE c.movie_tmdb_id = %s AND c.credit_type = 'cast'
            ORDER BY c.cast_order
            LIMIT 5
        """
        cursor.execute(cast_query, (movie_data[0],))
        cast_results = cursor.fetchall()
        cast = [c[0] for c in cast_results] if cast_results else []
        
        # Extract year
        year_val = movie_data[7] if movie_data[7] else 0
        
        result = {
            "tmdb_id": movie_data[0],
            "title": f"{movie_data[1]} ({year_val})" if movie_data[1] else "Unknown Movie",
            "genre": movie_data[6] if movie_data[6] else "N/A",
            "duration": 0,  # DB doesn't have runtime
            "cast": cast,
            "rating": float(movie_data[5]) if movie_data[5] else 0.0,
            "region": "Unknown",  # DB doesn't have production_countries
            "overview": movie_data[3] if movie_data[3] else "No overview available"
        }
        
        cursor.close()
        return result
        
    except Exception as e:
        logger.error(f"❌ Error searching from DB: {e}", exc_info=True)
        cursor.close()
        return None


def _search_from_tmdb_with_save(
    genres: List[str] = None,
    year: List[str] = None
) -> Optional[Dict]:
    """
    Fallback: Search movies from TMDb API + Auto-save to DB
    
    ✅ NEW: After finding movie, saves it to PostgreSQL for future queries
    """
    try:
        tmdb = get_tmdb_client()
        
        if not tmdb.api_key:
            logger.warning("⚠️ TMDb API key not configured")
            return None
        
        # Prepare discover params
        params = {
            "sort_by": "popularity.desc",
            "page": 1
        }
        
        # Add genre filter
        if genres:
            # Map genre names to TMDb genre IDs
            genre_map = {
                "Action": 28,
                "Adventure": 12,
                "Animation": 16,
                "Comedy": 35,
                "Crime": 80,
                "Documentary": 99,
                "Drama": 18,
                "Family": 10751,
                "Fantasy": 14,
                "History": 36,
                "Horror": 27,
                "Music": 10402,
                "Mystery": 9648,
                "Romance": 10749,
                "Science Fiction": 878,
                "Sci-Fi": 878,
                "TV Movie": 10770,
                "Thriller": 53,
                "War": 10752,
                "Western": 37
            }
            
            genre_ids = []
            for genre in genres:
                genre_id = genre_map.get(genre.strip())
                if genre_id:
                    genre_ids.append(str(genre_id))
            
            if genre_ids:
                params["with_genres"] = ",".join(genre_ids)
                logger.info(f"🎭 TMDb genre filter: {params['with_genres']}")
        
        # Add year filter
        if year and len(year) > 0:
            try:
                params["primary_release_year"] = int(year[0])
                logger.info(f"📅 TMDb year filter: {params['primary_release_year']}")
            except ValueError:
                pass
        
        # Call TMDb discover
        logger.info(f"📡 Calling TMDb discover with params: {params}")
        movies = tmdb.discover_movies(**params)
        
        if not movies:
            logger.warning("📭 No movies from TMDb discover")
            return None
        
        logger.info(f"📊 TMDb returned {len(movies)} movies")
        
        # Get random movie from results
        movie = random.choice(movies[:10])  # Pick from top 10
        tmdb_id = movie['id']
        
        # Get credits
        credits = tmdb.get_movie_credits(tmdb_id)
        cast = []
        if credits and 'cast' in credits:
            cast = [c['name'] for c in credits['cast'][:5]]
        
        # Get details for runtime and production countries
        details = tmdb.get_movie_details(tmdb_id)
        
        # Get country
        region = "Unknown"
        if details and 'production_countries' in details:
            countries = details.get('production_countries', [])
            if countries and len(countries) > 0:
                region = countries[0].get('name', 'Unknown')
        
        # Get genres
        genre_names = []
        if details and 'genres' in details:
            genre_names = [g['name'] for g in details['genres']]
        
        # Extract year from release_date
        release_year = ""
        if movie.get('release_date'):
            release_year = movie['release_date'][:4]
        
        # ✅ NEW: Save movie to database + FAISS for future use
        try:
            logger.info(f"💾 Saving movie to DB: {movie['title']} ({release_year})")
            from peninemate.core_logic.db_ops import save_movie_to_db
            save_success = save_movie_to_db(tmdb_id)
            
            if save_success:
                logger.info(f"✅ Movie saved to DB successfully")
                
                # ✅ ALSO: Add to FAISS index
                try:
                    from peninemate.core_logic.faiss_ops import add_movie_to_faiss
                    add_movie_to_faiss(tmdb_id)
                    logger.info(f"✅ Movie added to FAISS index")
                except Exception as faiss_error:
                    logger.warning(f"⚠️ Could not add to FAISS: {faiss_error}")
            
        except Exception as save_error:
            logger.warning(f"⚠️ Could not save movie to DB: {save_error}")
            # Continue anyway - saving is optional
        
        result = {
            "tmdb_id": tmdb_id,
            "title": f"{movie['title']} ({release_year})" if movie.get('title') else "Unknown Movie",
            "genre": ", ".join(genre_names) if genre_names else "N/A",
            "duration": details.get('runtime', 0) if details else 0,
            "cast": cast,
            "rating": float(movie.get('vote_average', 0.0)),
            "region": region,
            "overview": movie.get('overview', 'No overview available')
        }
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Error searching from TMDb: {e}", exc_info=True)
        return None
