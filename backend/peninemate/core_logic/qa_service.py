"""
Q&A Service with LLM Integration
Handles movie questions with context awareness
"""

import logging
import re
from typing import List, Dict, Tuple, Optional
from peninemate.core_logic.search_orchestrator import get_search_orchestrator
from peninemate.infrastructure.llm_client import get_llm_client
from peninemate.infrastructure.tmdb_client import get_tmdb_client
from peninemate.core_logic.qa_db import get_movie_by_tmdb_id

logger = logging.getLogger(__name__)


def answer_question_with_llm(
    question: str,
    conversation_history: Optional[List[Dict[str, str]]] = None
) -> Tuple[str, List[Dict], str]:
    """
    Answer movie questions with LLM-generated natural language responses
    Flow: FAISS/DB → TMDb fallback → LLM answer generation
    
    Args:
        question: User's question
        conversation_history: Previous conversation messages
    
    Returns:
        Tuple of (answer, movies, source)
    """
    logger.info(f"🤖 Q&A: '{question}'")
    
    if conversation_history is None:
        conversation_history = []
    
    # ✅ NEW: Use context-aware search
    orchestrator = get_search_orchestrator()
    movies, source = orchestrator.search_with_context(
        question, 
        conversation_history=conversation_history,
        limit=5
    )
    
    # Step 2: If no results, try TMDb API fallback
    if not movies or len(movies) == 0:
        logger.info("📭 No results from DB/FAISS, trying TMDb fallback...")
        tmdb_movie = _search_tmdb_fallback(question)
        
        if tmdb_movie:
            movies = [tmdb_movie]
            source = "tmdb_api"
            logger.info(f"✅ TMDb fallback success: {tmdb_movie['title']}")
        else:
            logger.warning("⚠️ No results from TMDb either")
    
    logger.info(f"🔍 Found {len(movies)} movies, best match: {movies[0]['title'] if movies else 'None'}")
    
    # Step 3: Generate answer with LLM
    llm = get_llm_client()
    
    # Build context from movies
    context = _build_context(movies, question)
    
    # Build conversation history string
    history_str = ""
    if conversation_history:
        for msg in conversation_history[-5:]:  # Last 5 messages
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            history_str += f"{role.capitalize()}: {content}\n"
    
    # Generate answer
    answer = llm.generate_answer(
        question=question,
        context=context,
        conversation_history=history_str
    )
    
    logger.info("✅ LLM answer generated")
    
    return answer, movies, source


def _search_tmdb_fallback(question: str) -> Optional[Dict]:
    """
    Fallback search using TMDb API when DB/FAISS have no results
    Extracts movie title from question and searches TMDb
    
    Args:
        question: User's question
    
    Returns:
        Movie dict or None
    """
    try:
        # Extract potential movie title from question
        # Simple extraction: look for quoted text or capitalized phrases
        
        # Try to find movie title in quotes
        quoted = re.findall(r'"([^"]+)"', question)
        if quoted:
            search_query = quoted[0]
        else:
            # Try to find title patterns like "Tell me about TITLE"
            patterns = [
                r'about (.+?)(?:\?|$|\()',
                r'(?:movie|film) (.+?)(?:\?|$|\()',
                r'tell me about (.+?)(?:\?|$|\()'
            ]
            
            search_query = None
            for pattern in patterns:
                match = re.search(pattern, question, re.IGNORECASE)
                if match:
                    search_query = match.group(1).strip()
                    break
            
            if not search_query:
                # Use entire question as search query
                search_query = question
        
        logger.info(f"🔍 TMDb search query: '{search_query}'")
        
        # Search TMDb
        tmdb = get_tmdb_client()
        results = tmdb.search_movies(search_query)
        
        if not results or 'results' not in results or len(results['results']) == 0:
            logger.info("📭 No TMDb results")
            return None
        
        # Get first result
        movie_data = results['results'][0]
        tmdb_id = movie_data['id']
        
        # Get detailed info
        details = tmdb.get_movie_details(tmdb_id)
        credits = tmdb.get_movie_credits(tmdb_id)
        
        # Extract year
        year = None
        if details and 'release_date' in details:
            year_str = details['release_date'][:4]
            try:
                year = int(year_str)
            except:
                pass
        
        # Extract genres
        genres_list = []
        if details and 'genres' in details:
            genres_list = [g['name'] for g in details['genres']]
        
        # Extract directors
        directors = []
        if credits and 'crew' in credits:
            directors = [c['name'] for c in credits['crew'] if c.get('job') == 'Director']
        
        # Extract cast
        cast = []
        if credits and 'cast' in credits:
            cast = [c['name'] for c in credits['cast'][:10]]
        
        # Build movie dict in same format as DB results
        movie = {
            'tmdb_id': tmdb_id,
            'title': details.get('title', movie_data.get('title', 'Unknown')),
            'year': year,
            'overview': details.get('overview', movie_data.get('overview', '')),
            'popularity': details.get('popularity', movie_data.get('popularity', 0)),
            'vote_average': details.get('vote_average', movie_data.get('vote_average', 0)),
            'genres_csv': ', '.join(genres_list),
            'directors': directors,
            'cast': cast,
            'runtime': details.get('runtime', 0) if details else 0
        }
        
        logger.info(f"✅ TMDb movie found: {movie['title']} ({movie['year']})")
        
        return movie
        
    except Exception as e:
        logger.error(f"❌ TMDb fallback error: {e}", exc_info=True)
        return None


def _build_context(movies: List[Dict], question: str) -> str:
    """
    Build context string from movie data for LLM
    
    Args:
        movies: List of movie dictionaries
        question: User's question
    
    Returns:
        Formatted context string
    """
    if not movies:
        return "No movie information available."
    
    context_parts = []
    
    for i, movie in enumerate(movies[:3], 1):  # Top 3 movies
        title = movie.get('title', 'Unknown')
        year = movie.get('year', 'N/A')
        overview = movie.get('overview', 'No overview available')
        popularity = movie.get('popularity', 0)
        rating = movie.get('vote_average', 0)
        genres = movie.get('genres_csv', 'Unknown')
        
        # Get directors and cast
        directors = movie.get('directors', [])
        cast = movie.get('cast', [])
        
        movie_info = f"""
Movie {i}: {title} ({year})
Genres: {genres}
Rating: {rating}/10 (Popularity: {popularity})
Overview: {overview}
"""
        
        if directors:
            movie_info += f"Director(s): {', '.join(directors[:3])}\n"
        
        if cast:
            movie_info += f"Cast: {', '.join(cast[:5])}\n"
        
        context_parts.append(movie_info.strip())
    
    return "\n\n".join(context_parts)


# ============================================================================
# Legacy function for backward compatibility
# ============================================================================

def answer_question_with_context(
    question: str,
    conversation_history: Optional[List[Dict[str, str]]] = None
) -> Tuple[str, List[Dict], str]:
    """
    Legacy wrapper - calls answer_question_with_llm
    Kept for backward compatibility
    """
    return answer_question_with_llm(question, conversation_history)