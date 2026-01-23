# peninemate/core_logic/qa_service.py

"""
Q&A Service dengan Hybrid Search + SMART LAZY LOADING + CONVERSATION CONTEXT
Auto-fetch missing movies from TMDb API and save to database
v5: Fixed context awareness and standardized return format
"""

import sys
from pathlib import Path
import logging
import re
from difflib import SequenceMatcher

# Add parent dir for imports
sys.path.insert(0, str(Path(__file__).parent))

import importlib
if 'search_orchestrator' in sys.modules:
    import peninemate.core_logic.search_orchestrator as search_orchestrator
    importlib.reload(search_orchestrator)

from peninemate.core_logic.search_orchestrator import get_search_orchestrator
from peninemate.infrastructure.tmdb_client import get_tmdb_client
from peninemate.core_logic.qa_db import (
    get_credits_for_movie,
    get_movie_by_tmdb_id,
    search_movies_by_director,
    search_movies_by_actor
)

logger = logging.getLogger(__name__)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def title_similarity(title1: str, title2: str) -> float:
    """Calculate similarity between two titles (0.0 to 1.0)"""
    return SequenceMatcher(None, title1.lower(), title2.lower()).ratio()


def is_likely_movie_title(query: str) -> bool:
    """
    Determine if query looks like a movie title vs semantic search
    """
    query_lower = query.lower()
    
    semantic_indicators = [
        'about', 'movie', 'movies', 'film', 'films',
        'action', 'comedy', 'drama', 'horror', 'thriller',
        'romantic', 'science fiction', 'sci-fi',
        'space', 'war', 'crime', 'adventure', 'fantasy',
        'best', 'top', 'popular', 'famous',
        'like', 'similar', 'recommend'
    ]
    
    indicator_count = sum(1 for ind in semantic_indicators if ind in query_lower)
    
    if indicator_count >= 2:
        return False
    
    question_words = ['what', 'which', 'who', 'when', 'where', 'why', 'how']
    if any(query_lower.startswith(qw) for qw in question_words):
        return False
    
    word_count = len(query.split())
    if word_count <= 5 and indicator_count == 0:
        return True
    
    return False


# ============================================================================
# DATABASE OPERATIONS
# ============================================================================

def save_movie_to_db(movie_data: dict) -> dict:
    """Save movie from TMDb API to database (LAZY LOADING)"""
    from peninemate.infrastructure.db_client import get_conn
    
    conn = get_conn()
    cur = conn.cursor()
    
    try:
        year = None
        if movie_data.get('release_date'):
            try:
                year = int(movie_data['release_date'][:4])
            except:
                pass
        
        cur.execute("""
            INSERT INTO movies (
                tmdb_id, title, year, overview, popularity,
                box_office_worldwide, box_office_domestic, box_office_foreign
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (tmdb_id) DO UPDATE SET
                title = EXCLUDED.title,
                year = EXCLUDED.year,
                overview = EXCLUDED.overview,
                popularity = EXCLUDED.popularity
            RETURNING tmdb_id, title, year, overview, popularity,
                box_office_worldwide, box_office_domestic, box_office_foreign
        """, (
            movie_data['id'],
            movie_data['title'],
            year,
            movie_data.get('overview'),
            movie_data.get('popularity'),
            movie_data.get('revenue'),
            None,
            None
        ))
        
        result = cur.fetchone()
        conn.commit()
        
        return {
            'tmdb_id': result[0],
            'title': result[1],
            'year': result[2],
            'overview': result[3],
            'popularity': result[4],
            'box_office_worldwide': result[5],
            'box_office_domestic': result[6],
            'box_office_foreign': result[7]
        }
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to save movie: {e}")
        return None
    finally:
        cur.close()


def get_credits_from_db(tmdb_id: int):
    """Get credits from DB, returns None if not found"""
    try:
        credits = get_credits_for_movie(tmdb_id)
        return credits if credits else None
    except:
        return None


def insert_credits_to_db(tmdb_id: int, credits_data: dict):
    """Insert credits to database"""
    from peninemate.infrastructure.db_client import get_conn
    
    conn = get_conn()
    cur = conn.cursor()
    
    try:
        # Delete existing credits
        cur.execute("DELETE FROM credits WHERE movie_tmdb_id = %s", (tmdb_id,))
        
        # Insert cast (top 20)
        for cast_member in credits_data.get('cast', [])[:20]:
            try:
                cur.execute("""
                    INSERT INTO people (tmdb_person_id, name, gender, known_for_department, profile_path)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (tmdb_person_id) DO UPDATE SET name = EXCLUDED.name
                    RETURNING tmdb_person_id
                """, (
                    cast_member['id'], cast_member.get('name'),
                    cast_member.get('gender'), cast_member.get('known_for_department'),
                    cast_member.get('profile_path')
                ))
                person_id = cur.fetchone()[0]
                
                cur.execute("""
                    INSERT INTO credits (
                        movie_tmdb_id, person_tmdb_person_id, credit_type,
                        character_name, cast_order
                    ) VALUES (%s, %s, 'cast', %s, %s)
                """, (tmdb_id, person_id, cast_member.get('character'), cast_member.get('order')))
            except:
                continue
        
        # Insert crew (Director, Writer, Producer, Screenplay)
        for crew_member in credits_data.get('crew', []):
            if crew_member.get('job') in ['Director', 'Writer', 'Producer', 'Screenplay']:
                try:
                    cur.execute("""
                        INSERT INTO people (tmdb_person_id, name, gender, known_for_department, profile_path)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (tmdb_person_id) DO UPDATE SET name = EXCLUDED.name
                        RETURNING tmdb_person_id
                    """, (
                        crew_member['id'], crew_member.get('name'),
                        crew_member.get('gender'), crew_member.get('known_for_department'),
                        crew_member.get('profile_path')
                    ))
                    person_id = cur.fetchone()[0]
                    
                    cur.execute("""
                        INSERT INTO credits (
                            movie_tmdb_id, person_tmdb_person_id, credit_type,
                            department, job
                        ) VALUES (%s, %s, 'crew', %s, %s)
                    """, (tmdb_id, person_id, crew_member.get('department'), crew_member.get('job')))
                except:
                    continue
        
        conn.commit()
        logger.info(f"✅ Lazy loaded credits for tmdb_id={tmdb_id}")
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to insert credits: {e}")
    finally:
        cur.close()


# ============================================================================
# SEARCH FUNCTIONS
# ============================================================================

def search_movie_hybrid(query: str, year: int = None, limit: int = 5):
    """
    SMART HYBRID SEARCH with LAZY LOADING + POPULARITY WEIGHTING:
    1. Search DB for exact match
    2. If no exact match, try TMDb API (with popularity weighting)
    3. Save best API result to DB automatically
    4. Return best result
    
    IMPROVED: Better handling for sequels (Iron Man 1, 2, 3, etc)
    
    Args:
        query: Movie title or description
        year: Release year (optional for filtering)
        limit: Max results
        
    Returns:
        List of movies with source annotation
    """
    orchestrator = get_search_orchestrator()
    
    # Phase 1: Search DB (keyword + semantic)
    db_results = orchestrator.search_hybrid(query, limit=limit)
    
    # Filter by year if specified
    if year and db_results:
        db_results = [r for r in db_results if r.get('year') == year]
    
    # Check if we have exact match in DB
    exact_match = None
    for r in db_results:
        if r['title'].lower() == query.lower():
            exact_match = r
            break
    
    # If exact match found, use it
    if exact_match:
        logger.info(f"✅ Exact match found in DB: {exact_match['title']} ({exact_match['year']})")
        return [exact_match] + [r for r in db_results if r['tmdb_id'] != exact_match['tmdb_id']][:limit-1]
    
    # ✅ NEW: Check if query contains numbers (likely sequel search)
    has_number = bool(re.search(r'\d', query))
    
    # Phase 2: No exact match - Try TMDb API if query looks like a title
    if is_likely_movie_title(query):
        logger.info(f"⚠️ No exact match for '{query}' in DB, checking TMDb API...")
        
        tmdb_client = get_tmdb_client()
        api_results = tmdb_client.search_movie(query, year=year)
        
        if api_results and isinstance(api_results, list) and len(api_results) > 0:
            logger.info(f"📡 TMDb API returned {len(api_results)} results")
            
            # Find best match from API results (with popularity weighting)
            best_api_result = None
            best_score = 0.0
            
            for api_movie in api_results:
                api_title = api_movie.get('title', '')
                api_popularity = api_movie.get('popularity', 0)
                api_year = None
                
                if api_movie.get('release_date'):
                    try:
                        api_year = int(api_movie['release_date'][:4])
                    except:
                        pass
                
                # Calculate title similarity (0.0 to 1.0)
                similarity = title_similarity(api_title, query)
                
                # Normalize popularity (0-100 typical range → 0-1)
                normalized_popularity = min(api_popularity / 50.0, 1.0)
                
                # Combined score
                if similarity == 1.0:
                    score = 0.7 * similarity + 0.3 * normalized_popularity
                    logger.info(f"  ✅ Exact: '{api_title}' ({api_year}) [pop: {api_popularity:.1f}, score: {score:.3f}]")
                elif similarity >= 0.6:
                    score = 0.8 * similarity + 0.2 * normalized_popularity
                    logger.info(f"  ⭐ Match: '{api_title}' ({api_year}) [sim: {similarity:.2f}, pop: {api_popularity:.1f}, score: {score:.3f}]")
                else:
                    continue
                
                if score > best_score:
                    best_score = score
                    best_api_result = api_movie
            
            if best_api_result:
                api_title = best_api_result.get('title', '')
                api_year = None
                if best_api_result.get('release_date'):
                    try:
                        api_year = int(best_api_result['release_date'][:4])
                    except:
                        pass
                
                api_similarity = title_similarity(api_title, query)
                logger.info(f"  📌 Best match: {api_title} ({api_year}) [similarity: {api_similarity:.2f}, final score: {best_score:.3f}]")
                
                # ✅ IMPROVED: Decide if API result is better than DB results
                is_better_match = False
                
                # Case 1: High similarity (>= 0.9) = almost exact match
                if api_similarity >= 0.9:
                    is_better_match = True
                    logger.info(f"  ✅ API is better (high similarity: {api_similarity:.2f})")
                
                # Case 2: Query has numbers (sequel search) AND similarity >= 0.7
                elif has_number and api_similarity >= 0.7:
                    is_better_match = True
                    logger.info(f"  ✅ API is better (sequel search: '{query}' has numbers, similarity: {api_similarity:.2f})")
                
                # Case 3: No DB results at all
                elif not db_results:
                    is_better_match = True
                    logger.info(f"  ✅ API is better (no DB results)")
                
                # Case 4: Compare with DB top result
                elif db_results:
                    db_similarity = title_similarity(db_results[0]['title'], query)
                    # Use API if significantly better (>0.2 difference)
                    if api_similarity > db_similarity + 0.2:
                        is_better_match = True
                        logger.info(f"  ✅ API is better (API: {api_similarity:.2f} >> DB: {db_similarity:.2f})")
                
                if is_better_match:
                    logger.info(f"💾 Saving '{api_title}' to database...")
                    saved_movie = save_movie_to_db(best_api_result)
                    
                    if saved_movie:
                        logger.info(f"  ✅ Saved! Future queries will use DB.")
                        api_movie_dict = {
                            'tmdb_id': saved_movie['tmdb_id'],
                            'title': saved_movie['title'],
                            'year': saved_movie['year'],
                            'overview': saved_movie.get('overview'),
                            'popularity': saved_movie.get('popularity'),
                            'source': 'tmdb_api_lazy_loaded'
                        }
                        return [api_movie_dict] + db_results[:limit-1]
    
    # Phase 3: Return DB results (partial matches) or empty
    if db_results:
        logger.info(f"⚠️ Returning partial matches from DB")
        return db_results[:limit]
    else:
        logger.info(f"❌ No results found for '{query}'")
        return []



# ============================================================================
# INTENT HANDLERS
# ============================================================================

def answer_director_question(title: str, year: int = None):
    """Answer: Who is the director of movie X?"""
    results = search_movie_hybrid(title, year=year, limit=1)
    
    if not results:
        return {
            "intent": "director",
            "found": False,
            "query": {"title": title, "year": year},
            "message": f"Film '{title}' tidak ditemukan.",
            "source": "none"
        }
    
    movie = results[0]
    tmdb_id = movie['tmdb_id']
    source = movie.get('source', 'hybrid')
    
    # Get credits (with lazy loading)
    credits = get_credits_from_db(tmdb_id)
    
    if not credits:
        logger.info(f"⚠️ No credits in DB for {movie['title']}, fetching from TMDb API...")
        tmdb_client = get_tmdb_client()
        movie_details = tmdb_client.get_movie_details(tmdb_id)
        
        if movie_details and movie_details.get('credits'):
            insert_credits_to_db(tmdb_id, movie_details['credits'])
            credits = movie_details['credits']
    
    # Extract directors
    directors = []
    if isinstance(credits, dict) and 'crew' in credits:
        directors = [p for p in credits['crew'] if p.get('job') == 'Director']
    elif isinstance(credits, list):
        directors = [c for c in credits if c.get('credit_type') == 'crew' and c.get('job') == 'Director']
    
    if not directors:
        return {
            "intent": "director",
            "found": True,
            "movie": {"tmdb_id": tmdb_id, "title": movie['title'], "year": movie['year']},
            "directors": [],
            "message": f"Informasi sutradara untuk '{movie['title']}' tidak tersedia.",
            "source": source
        }
    
    return {
        "intent": "director",
        "found": True,
        "movie": {"tmdb_id": tmdb_id, "title": movie['title'], "year": movie['year']},
        "directors": [d.get('name') or d.get('person_name') for d in directors],
        "source": source
    }


def answer_cast_question(title: str, year: int = None, limit: int = 5):
    """Answer: Who are the actors in movie X?"""
    results = search_movie_hybrid(title, year=year, limit=1)
    
    if not results:
        return {
            "intent": "cast",
            "found": False,
            "query": {"title": title, "year": year},
            "message": f"Film '{title}' tidak ditemukan.",
            "source": "none"
        }
    
    movie = results[0]
    tmdb_id = movie['tmdb_id']
    source = movie.get('source', 'hybrid')
    
    # Get credits (with lazy loading)
    credits = get_credits_for_movie(tmdb_id)
    
    if not credits:
        logger.info(f"⚠️ No credits in DB for {movie['title']}, fetching from TMDb API...")
        tmdb_client = get_tmdb_client()
        movie_details = tmdb_client.get_movie_details(tmdb_id)
        
        if movie_details and movie_details.get('credits'):
            insert_credits_to_db(tmdb_id, movie_details['credits'])
            credits = movie_details['credits']
    
    # Extract cast
    cast = []
    if isinstance(credits, dict) and 'cast' in credits:
        cast = credits['cast'][:limit]
    elif isinstance(credits, list):
        cast = [c for c in credits if c.get('credit_type') == 'cast'][:limit]
    
    return {
        "intent": "cast",
        "found": True,
        "movie": {"tmdb_id": tmdb_id, "title": movie['title'], "year": movie['year']},
        "cast": [
            {
                "name": c.get('name') or c.get('person_name'),
                "character": c.get('character') or c.get('character_name')
            }
            for c in cast
        ],
        "source": source
    }


def answer_year_question(title: str):
    """Answer: When was movie X released?"""
    results = search_movie_hybrid(title, limit=1)
    
    if not results:
        return {
            "intent": "year",
            "found": False,
            "query": {"title": title},
            "message": f"Film '{title}' tidak ditemukan.",
            "source": "none"
        }
    
    movie = results[0]
    return {
        "intent": "year",
        "found": True,
        "movie": {"tmdb_id": movie['tmdb_id'], "title": movie['title'], "year": movie['year']},
        "source": movie.get('source', 'hybrid')
    }


def answer_plot_question(title: str, year: int = None):
    """Answer: What is the plot of movie X?"""
    results = search_movie_hybrid(title, year=year, limit=1)
    
    if not results:
        return {
            "intent": "plot",
            "found": False,
            "query": {"title": title, "year": year},
            "message": f"Film '{title}' tidak ditemukan.",
            "source": "none"
        }
    
    movie = results[0]
    return {
        "intent": "plot",
        "found": True,
        "movie": {
            "tmdb_id": movie['tmdb_id'],
            "title": movie['title'],
            "year": movie['year'],
            "overview": movie.get('overview', 'Plot tidak tersedia.')
        },
        "source": movie.get('source', 'hybrid')
    }


def answer_box_office_question(title: str, year: int = None):
    """Answer: How much did movie X earn?"""
    results = search_movie_hybrid(title, year=year, limit=1)
    
    if not results:
        return {
            "intent": "box_office",
            "found": False,
            "query": {"title": title, "year": year},
            "message": f"Film '{title}' tidak ditemukan.",
            "source": "none"
        }
    
    movie = results[0]
    tmdb_id = movie['tmdb_id']
    
    # Get full movie data
    movie_data = get_movie_by_tmdb_id(tmdb_id)
    
    box_office = {}
    if movie_data:
        box_office = {
            "worldwide": movie_data.get('box_office_worldwide'),
            "domestic": movie_data.get('box_office_domestic'),
            "foreign": movie_data.get('box_office_foreign')
        }
    
    return {
        "intent": "box_office",
        "found": True,
        "movie": {"tmdb_id": tmdb_id, "title": movie['title'], "year": movie['year']},
        "box_office": box_office,
        "source": movie.get('source', 'hybrid')
    }

def answer_actor_filmography_question(actor_name: str, limit: int = 10):
    """
    Answer: What movies did actor X star in?
    
    Args:
        actor_name: Name of the actor
        limit: Max number of movies to return
        
    Returns:
        Intent result dictionary
    """
    from peninemate.core_logic.qa_db import search_movies_by_actor
    
    logger.info(f"🎬 Searching filmography for actor: '{actor_name}'")
    
    # Search movies by actor
    movies = search_movies_by_actor(actor_name, limit=limit)
    
    if not movies:
        return {
            "intent": "actor_filmography",
            "found": False,
            "query": {"actor": actor_name},
            "message": f"No movies found for actor '{actor_name}'.",
            "source": "none"
        }
    
    return {
        "intent": "actor_filmography",
        "found": True,
        "actor": actor_name,
        "movies": movies,
        "source": "database"
    }

def answer_director_filmography_question(director_name: str, limit: int = 10):
    """
    Answer: What movies did director X make?
    
    Args:
        director_name: Name of the director
        limit: Max number of movies to return
        
    Returns:
        Intent result dictionary
    """
    from peninemate.core_logic.qa_db import search_movies_by_director
    
    logger.info(f"🎬 Searching filmography for director: '{director_name}'")
    
    # Search movies by director
    movies = search_movies_by_director(director_name, limit=limit)
    
    if not movies:
        return {
            "intent": "director_filmography",
            "found": False,
            "query": {"director": director_name},
            "message": f"No movies found for director '{director_name}'.",
            "source": "none"
        }
    
    return {
        "intent": "director_filmography",
        "found": True,
        "director": director_name,
        "movies": movies,
        "source": "database"
    }

# ============================================================================
# RESPONSE FORMATTER
# ============================================================================

def format_response(intent_result: dict) -> tuple:
    """
    Convert intent result dict to standardized tuple format
    
    Args:
        intent_result: Dictionary from answer_*_question functions
        
    Returns:
        tuple: (answer, movies, source) - ALWAYS 3 VALUES
    """
    intent = intent_result.get('intent', 'unknown')
    found = intent_result.get('found', False)
    source = intent_result.get('source', 'unknown')
    
    if not found:
        return (
            intent_result.get('message', 'Tidak ditemukan.'),
            [],
            source
        )
    
    movies = []
    answer = ""
    
    if intent == 'director':
        movie = intent_result.get('movie', {})
        directors = intent_result.get('directors', [])
        movies = [movie] if movie else []
        
        if directors:
            director_names = ', '.join(directors)
            answer = f"{director_names} directed {movie['title']} ({movie.get('year', 'N/A')})."
        else:
            answer = intent_result.get('message', 'Informasi sutradara tidak tersedia.')
    
    elif intent == 'cast':
        movie = intent_result.get('movie', {})
        cast = intent_result.get('cast', [])
        movies = [movie] if movie else []
        
        if cast:
            cast_names = [c['name'] for c in cast[:5]]
            answer = f"Cast of {movie['title']} ({movie.get('year', 'N/A')}): {', '.join(cast_names)}."
        else:
            answer = intent_result.get('message', 'Informasi cast tidak tersedia.')
    
    elif intent == 'plot':
        movie = intent_result.get('movie', {})
        movies = [movie] if movie else []
        overview = movie.get('overview', 'Plot tidak tersedia.')
        answer = f"{movie['title']} ({movie.get('year', 'N/A')}): {overview}"
    
    elif intent == 'year':
        movie = intent_result.get('movie', {})
        movies = [movie] if movie else []
        answer = f"{movie['title']} was released in {movie.get('year', 'N/A')}."
    
    elif intent == 'box_office':
        movie = intent_result.get('movie', {})
        box_office = intent_result.get('box_office', {})
        movies = [movie] if movie else []
        
        worldwide = box_office.get('worldwide')
        if worldwide:
            answer = f"{movie['title']} ({movie.get('year', 'N/A')}) earned ${worldwide:,.0f} worldwide."
        else:
            answer = f"Box office information for {movie['title']} is not available."
    
    # ✅ NEW: Actor filmography
    elif intent == 'actor_filmography':
        actor = intent_result.get('actor', '')
        movies = intent_result.get('movies', [])
        
        if movies:
            movie_titles = [f"{m['title']} ({m.get('year', 'N/A')})" for m in movies[:5]]
            if len(movies) > 5:
                answer = f"{actor} starred in {len(movies)} movies including: {', '.join(movie_titles)}, and more."
            else:
                answer = f"{actor} starred in: {', '.join(movie_titles)}."
        else:
            answer = intent_result.get('message', f"No movies found for {actor}.")
    
    # ✅ NEW: Director filmography
    elif intent == 'director_filmography':
        director = intent_result.get('director', '')
        movies = intent_result.get('movies', [])
        
        if movies:
            movie_titles = [f"{m['title']} ({m.get('year', 'N/A')})" for m in movies[:5]]
            if len(movies) > 5:
                answer = f"{director} directed {len(movies)} movies including: {', '.join(movie_titles)}, and more."
            else:
                answer = f"{director} directed: {', '.join(movie_titles)}."
        else:
            answer = intent_result.get('message', f"No movies found for {director}.")
    
    else:
        answer = intent_result.get('message', 'Tidak ada hasil.')
    
    return (answer, movies, source)

# ============================================================================
# MAIN Q&A FUNCTIONS
# ============================================================================

def answer_question_with_context(question: str, conversation_history: list = None) -> tuple:
    """
    Answer question with conversation context awareness
    
    IMPROVED:
    - Extract movies, actors, and directors from conversation history
    - Detect follow-up questions about actors/directors
    - Smart context detection with new question filtering
    
    Args:
        question: Current user question
        conversation_history: List of {role, content} messages
        
    Returns:
        tuple: (answer_string, movies_list, source_string) - ALWAYS 3 VALUES
    """
    if not conversation_history:
        conversation_history = []
    
    logger.info(f"📝 Processing question: '{question}'")
    logger.info(f"📚 Conversation history: {len(conversation_history)} messages")
    
    # ============================================================================
    # EXTRACT CONTEXT FROM HISTORY
    # ============================================================================
    
    mentioned_movies = []
    mentioned_actors = []
    mentioned_directors = []
    
    for msg in conversation_history:
        if msg.get('role') == 'assistant':
            content = msg.get('content', '')
            
            # ✅ Extract MOVIES from history
            # Pattern to extract movie title after "of/for/in" keywords
            movie_pattern = r'(?:of|for|in)\s+([A-Z][A-Za-z0-9\s:,\'-]+?)\s*\((\d{4})\)'
            movie_matches = re.findall(movie_pattern, content)
            
            for title, year in movie_matches:
                title = title.strip()
                title = re.sub(r'\s+', ' ', title)  # Normalize spaces
                title = title.rstrip(':.,;!?')  # Remove trailing punctuation
                
                if len(title) > 2:
                    mentioned_movies.append({
                        'title': title,
                        'year': int(year)
                    })
                    logger.info(f"  📌 Found movie in history: {title} ({year})")
            
            # ✅ Extract ACTORS from "Cast of Movie: Actor1, Actor2, ..." responses
            cast_pattern = r'Cast of [^:]+:\s*([^.]+)'
            cast_match = re.search(cast_pattern, content)
            if cast_match:
                actor_list_str = cast_match.group(1)
                # Split by comma and clean up
                actor_names = [name.strip().rstrip('.') for name in actor_list_str.split(',')]
                
                for actor_name in actor_names[:5]:  # Take first 5 actors
                    if actor_name and len(actor_name) > 2:
                        # Clean up extra info (e.g., "Robert Downey Jr. (Tony Stark)" -> "Robert Downey Jr.")
                        clean_name = re.sub(r'\s*\([^)]+\)', '', actor_name).strip()
                        if clean_name:
                            mentioned_actors.append(clean_name)
                            logger.info(f"  👤 Found actor in history: {clean_name}")
            
            # ✅ Extract DIRECTORS from "Director directed Movie" responses
            director_pattern = r'^([A-Z][A-Za-z\s.]+?)\s+directed\s+'
            director_match = re.search(director_pattern, content)
            if director_match:
                director_name = director_match.group(1).strip()
                if director_name and len(director_name) > 2:
                    mentioned_directors.append(director_name)
                    logger.info(f"  🎬 Found director in history: {director_name}")
    
    # ============================================================================
    # DEDUPLICATE AND GET LAST MENTIONED ENTITIES
    # ============================================================================
    
    # Remove duplicate movies (keep last occurrence)
    seen_movies = set()
    unique_movies = []
    for movie in reversed(mentioned_movies):
        key = (movie['title'].lower(), movie['year'])
        if key not in seen_movies:
            seen_movies.add(key)
            unique_movies.append(movie)
    mentioned_movies = list(reversed(unique_movies))
    
    # Remove duplicate actors (keep last occurrence)
    seen_actors = set()
    unique_actors = []
    for actor in reversed(mentioned_actors):
        key = actor.lower()
        if key not in seen_actors:
            seen_actors.add(key)
            unique_actors.append(actor)
    mentioned_actors = list(reversed(unique_actors))
    
    # Remove duplicate directors (keep last occurrence)
    seen_directors = set()
    unique_directors = []
    for director in reversed(mentioned_directors):
        key = director.lower()
        if key not in seen_directors:
            seen_directors.add(key)
            unique_directors.append(director)
    mentioned_directors = list(reversed(unique_directors))
    
    # Get last mentioned entities
    last_mentioned_movie = mentioned_movies[-1] if mentioned_movies else None
    last_mentioned_actor = mentioned_actors[-1] if mentioned_actors else None
    last_mentioned_director = mentioned_directors[-1] if mentioned_directors else None
    
    if last_mentioned_movie:
        logger.info(f"🎬 Last mentioned movie: {last_mentioned_movie['title']} ({last_mentioned_movie['year']})")
    if last_mentioned_actor:
        logger.info(f"👤 Last mentioned actor: {last_mentioned_actor}")
    if last_mentioned_director:
        logger.info(f"🎬 Last mentioned director: {last_mentioned_director}")
    
    # ============================================================================
    # DETECT QUESTION TYPE AND CONTEXT USAGE
    # ============================================================================
    
    question_lower = question.lower()
    
    # ✅ Check patterns that indicate NEW question (not follow-up)
    # If question has content words after "cast/director/plot" keywords, likely a new question
    
    new_question_patterns = [
        r'cast\s+(?:of|in|from)\s+(\w+)',  # "cast of iron", "cast of avengers"
        r'(?:who|siapa)\s+(?:directed|made|sutradara)\s+(\w+)',  # "who directed inception"
        r'(?:plot|story|cerita)\s+(?:of|from)\s+(\w+)',  # "plot of titanic"
        r'(?:what|apa)\s+(?:is|about)\s+(\w+)',  # "what is inception about"
    ]
    
    is_new_question = False
    for pattern in new_question_patterns:
        match = re.search(pattern, question_lower)
        if match:
            # Extract the potential movie name
            potential_movie = match.group(1)
            # If it's not a pronoun/article, likely a new movie name
            pronouns = ['it', 'that', 'this', 'the', 'a', 'an']
            if potential_movie not in pronouns:
                is_new_question = True
                logger.info(f"  🆕 Detected new question (not follow-up): found '{potential_movie}' after keyword")
                break
    
    # ============================================================================
    # ACTOR FILMOGRAPHY CONTEXT
    # ============================================================================
    
    # Check if question is about actor filmography
    actor_filmography_keywords = [
        'other movies', 'what movies', 'what films', 'what else',
        'starred in', 'acted in', 'appeared in', 'played in',
        'filmography', 'film lain', 'movie lain'
    ]
    
    is_actor_filmography = any(kw in question_lower for kw in actor_filmography_keywords)
    
    if is_actor_filmography and last_mentioned_actor and not is_new_question:
        logger.info(f"✅ Actor filmography context detected")
        modified_question = f"What movies did {last_mentioned_actor} star in"
        logger.info(f"🔄 Transformed to: '{modified_question}'")
        return answer_question(modified_question)
    
    # ============================================================================
    # DIRECTOR FILMOGRAPHY CONTEXT
    # ============================================================================
    
    # Check if question is about director filmography
    director_filmography_keywords = [
        'other films by', 'what films did', 'what movies did',
        'directed what', 'made what', 'filmography'
    ]
    
    is_director_filmography = any(kw in question_lower for kw in director_filmography_keywords)
    
    if is_director_filmography and last_mentioned_director and not is_new_question:
        logger.info(f"✅ Director filmography context detected")
        modified_question = f"What movies did {last_mentioned_director} direct"
        logger.info(f"🔄 Transformed to: '{modified_question}'")
        return answer_question(modified_question)
    
    # ============================================================================
    # MOVIE CONTEXT (ORIGINAL LOGIC)
    # ============================================================================
    
    # Define pure contextual keywords (questions WITHOUT movie names)
    pure_contextual_keywords = [
        'that film', 'that movie', 'the film', 'the movie', 'this film', 'this movie',
        'it', 'about it', 'the cast', 'the director', 'the plot', 'the story',
        'when was it released', 'what genre is it', 'who acted in it',
        'film itu', 'siapa pemainnya', 'siapa sutradaranya'
    ]
    
    # Check if question uses pure contextual keywords
    has_contextual_keyword = any(kw in question_lower for kw in pure_contextual_keywords)
    
    # ✅ FINAL DECISION: Only use movie context if:
    # 1. Has pure contextual keyword (like "it", "that film", "the cast" without movie name)
    # 2. Is NOT detected as new question
    # 3. Has last mentioned movie
    
    if has_contextual_keyword and not is_new_question and last_mentioned_movie:
        logger.info(f"✅ Movie context detected in: '{question}'")
        
        modified_question = question
        title = last_mentioned_movie['title']
        
        # Smart question reconstruction based on keyword
        if 'cast' in question_lower:
            modified_question = f"Who is the cast of {title}"
        elif 'director' in question_lower or 'sutradara' in question_lower:
            modified_question = f"Who directed {title}"
        elif 'plot' in question_lower or 'story' in question_lower or 'about' in question_lower:
            modified_question = f"What is the plot of {title}"
        elif 'year' in question_lower or 'when' in question_lower or 'released' in question_lower:
            modified_question = f"When was {title} released"
        else:
            # Generic replacement for "it", "that film"
            for keyword in ['that film', 'that movie', 'this film', 'this movie', 'it']:
                if keyword in question_lower:
                    idx = question_lower.find(keyword)
                    modified_question = (
                        question[:idx] + 
                        title + 
                        question[idx + len(keyword):]
                    )
                    break
        
        logger.info(f"🔄 Transformed to: '{modified_question}'")
        return answer_question(modified_question)
    
    # ============================================================================
    # NO CONTEXT - STANDALONE QUESTION
    # ============================================================================
    
    # No context reference, use original function
    logger.info(f"ℹ️ No context detected, processing as standalone question")
    return answer_question(question)


def answer_question(question: str) -> tuple:
    """
    Main Q&A function with improved regex patterns
    
    Args:
        question: Natural language question
        
    Returns:
        tuple: (answer_string, movies_list, source_string) - ALWAYS 3 VALUES
    """
    question_lower = question.lower().strip()
    
    # Director patterns
    director_patterns = [
        r'(?:who|siapa)\s+(?:directed|made|sutradara|filmmaker\s+of)\s+(.+?)(?:\?|$)',
        r'(?:director|sutradara)\s+(?:of|dari)\s+(.+?)(?:\?|$)',
        r'who(?:\'s| is)\s+the\s+director\s+(?:of|for)\s+(.+?)(?:\?|$)',
        r'siapa\s+yang\s+(?:menyutradarai|mengarahkan)\s+(.+?)(?:\?|$)',
        r'who\s+made\s+(.+?)(?:\?|$)',
    ]
    
    # Cast patterns
    cast_patterns = [
        r'(?:who|siapa)\s+(?:are\s+the\s+|is\s+the\s+|pemain\s+)?(?:actors?|cast|stars?|pemain)\s+(?:in|of|from|for)\s+(.+?)(?:\?|$)',
        r'cast\s+(?:of|from|in|for)\s+(.+?)(?:\?|$)',
        r'(?:actors?|pemain|stars?)\s+(?:in|of|from|for)\s+(.+?)(?:\?|$)',
        r'siapa\s+(?:yang\s+)?main\s+(?:di|dalam)\s+(.+?)(?:\?|$)',
        r'who\s+(?:starred\s+in|acted\s+in|featured\s+in|plays\s+in)\s+(.+?)(?:\?|$)',
    ]
    
    # Plot patterns
    plot_patterns = [
        r'tell\s+me\s+about\s+(.+?)(?:\?|$)',
        r'(?:what|apa)\s+(?:is|about)\s+(.+?)\s+about(?:\?|$)',
        r'(?:plot|story|cerita|synopsis|storyline)\s+(?:of|from)\s+(.+?)(?:\?|$)',
        r'what(?:\'s| is)\s+(.+?)\s+about(?:\?|$)',
        r'describe\s+(.+?)(?:\?|$)',
        r'summary\s+(?:of|for)\s+(.+?)(?:\?|$)',
    ]
    
    # Year patterns
    year_patterns = [
        r'when\s+(?:was|did)\s+(.+?)\s+(?:released|come\s+out|premiere)(?:\?|$)',
        r'what\s+year\s+(?:did|was)\s+(.+?)\s+(?:released|come\s+out|made)(?:\?|$)',
        r'when\s+(?:did|was)\s+(.+?)\s+(?:release|come\s+out)(?:\?|$)',
        r'release\s+(?:date|year)\s+(?:of|for)\s+(.+?)(?:\?|$)',
        r'kapan\s+(.+?)\s+rilis(?:\?|$)',
    ]
    
    # Box office patterns
    box_office_patterns = [
        r'(?:how\s+much|berapa)\s+(?:did|money|revenue)\s+(.+?)\s+(?:earn|make|gross)(?:\?|$)',
        r'(?:box\s+office|earnings|revenue)\s+(?:of|for|from)\s+(.+?)(?:\?|$)',
    ]
    
    # ✅ NEW: Actor filmography patterns
    actor_filmography_patterns = [
        r'what\s+(?:other\s+)?movies\s+(?:does|did)\s+(.+?)\s+(?:star\s+in|act\s+in|appear\s+in|play\s+in)(?:\?|$)',
        r'(?:films?|movies?)\s+(?:by|with|starring|featuring)\s+(.+?)(?:\?|$)',
        r'(?:show|list|tell)\s+(?:me\s+)?(?:films?|movies?)\s+(?:with|starring|by)\s+(.+?)(?:\?|$)',
        r'(.+?)\s+(?:filmography|movies|films)(?:\?|$)',
        r'what\s+(?:has|did)\s+(.+?)\s+(?:starred|acted|played)\s+in(?:\?|$)',
    ]
    
    # ✅ NEW: Director filmography patterns
    director_filmography_patterns = [
        r'what\s+(?:movies|films)\s+(?:did|has)\s+(.+?)\s+(?:direct|make)(?:\?|$)',
        r'(?:films?|movies?)\s+(?:directed\s+by|made\s+by|from)\s+(.+?)(?:\?|$)',
        r'(.+?)\s+(?:directed|made)\s+what\s+(?:films?|movies?)(?:\?|$)',
        r'list\s+(?:of\s+)?(?:films?|movies?)\s+(?:by|from)\s+director\s+(.+?)(?:\?|$)',
    ]
    
    # Try director
    for pattern in director_patterns:
        match = re.search(pattern, question_lower, re.IGNORECASE)
        if match:
            title = match.group(1).strip()
            result = answer_director_question(title)
            return format_response(result)
    
    # Try cast
    for pattern in cast_patterns:
        match = re.search(pattern, question_lower, re.IGNORECASE)
        if match:
            title = match.group(1).strip()
            result = answer_cast_question(title, limit=5)
            return format_response(result)
    
    # ✅ NEW: Try actor filmography
    for pattern in actor_filmography_patterns:
        match = re.search(pattern, question_lower, re.IGNORECASE)
        if match:
            actor_name = match.group(1).strip()
            logger.info(f"🎭 Detected actor filmography query for: '{actor_name}'")
            result = answer_actor_filmography_question(actor_name, limit=10)
            return format_response(result)
    
    # ✅ NEW: Try director filmography
    for pattern in director_filmography_patterns:
        match = re.search(pattern, question_lower, re.IGNORECASE)
        if match:
            director_name = match.group(1).strip()
            logger.info(f"🎬 Detected director filmography query for: '{director_name}'")
            result = answer_director_filmography_question(director_name, limit=10)
            return format_response(result)
    
    # Try plot
    for pattern in plot_patterns:
        match = re.search(pattern, question_lower, re.IGNORECASE)
        if match:
            title = match.group(1).strip()
            result = answer_plot_question(title)
            return format_response(result)
    
    # Try year
    for pattern in year_patterns:
        match = re.search(pattern, question_lower, re.IGNORECASE)
        if match:
            title = match.group(1).strip()
            result = answer_year_question(title)
            return format_response(result)
    
    # Try box office
    for pattern in box_office_patterns:
        match = re.search(pattern, question_lower, re.IGNORECASE)
        if match:
            title = match.group(1).strip()
            result = answer_box_office_question(title)
            return format_response(result)
    
    # Fallback: Semantic search
    logger.info("⚠️ No specific pattern matched, using semantic search fallback")
    results = search_movie_hybrid(question, limit=5)
    
    if results:
        movie = results[0]
        overview = movie.get('overview', 'No description available.')
        answer_text = f"{movie['title']} ({movie.get('year', 'N/A')}): {overview}"
        return (answer_text, results, results[0].get('source', 'hybrid'))
    else:
        return ("Sorry, I couldn't find any relevant movies for your question.", [], 'none')
