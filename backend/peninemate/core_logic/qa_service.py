"""
Q&A Service - Improved Architecture
Flow: LLM Intent → Targeted Search → Fallback Chain → LLM Answer Generation
"""

import logging
from typing import List, Dict, Tuple, Optional
from enum import Enum

from peninemate.core_logic.search_orchestrator import get_search_orchestrator
from peninemate.infrastructure.llm_client import get_llm_client
from peninemate.infrastructure.tmdb_client import get_tmdb_client
from peninemate.core_logic.qa_db import get_movie_by_tmdb_id

logger = logging.getLogger(__name__)

# Context tracking
_last_discussed_movie = None


class QueryIntent(Enum):
    """Query intent types"""
    CAST = "cast"
    DIRECTOR = "director"
    PLOT = "plot"
    YEAR = "year"
    RATING = "rating"
    GENRE = "genre"
    RUNTIME = "runtime"
    LOCATION = "location"  # ← ADDED
    FRANCHISE = "franchise"
    RECOMMENDATION = "recommendation"
    GENERAL_INFO = "general_info"
    MOVIE_INFO = "movie_info"
    ENTITY_SEARCH = "entity_search"
    UNKNOWN = "unknown"


class SearchResult:
    """Search result container"""
    def __init__(self, movies: List[Dict], source: str, intent: QueryIntent):
        self.movies = movies
        self.source = source  # 'faiss', 'postgresql', 'tmdb_api'
        self.intent = intent


def answer_question_with_llm(
    question: str,
    conversation_history: Optional[List[Dict[str, str]]] = None
) -> Tuple[str, List[Dict], str]:
    """
    Main Q&A pipeline with improved architecture
    
    Pipeline:
    1. LLM analyzes intent and extracts search parameters
    2. Targeted search with fallback chain (FAISS → PostgreSQL → TMDb)
    3. LLM generates natural language answer
    """
    global _last_discussed_movie
    
    logger.info(f"🤖 Processing question: '{question}'")
    
    if conversation_history is None:
        conversation_history = []
    
    # ===== STEP 1: LLM Intent Analysis =====
    intent_analysis = _analyze_intent_with_llm(question, conversation_history)
    
    if not intent_analysis:
        return _generate_fallback_response(question), [], "none"
    
    logger.info(f"🧠 Intent: {intent_analysis['intent']}, Entity: {intent_analysis.get('movie_entity')}")
    
    # ===== STEP 2: Targeted Database Search =====
    search_result = _execute_targeted_search(intent_analysis)
    
    if not search_result or not search_result.movies:
        return _generate_no_result_response(question, intent_analysis), [], "none"
    
    logger.info(f"✅ Found {len(search_result.movies)} results from {search_result.source}")
    
    # ✅✅✅ FIX: Update context with first movie (dict), not the list
    _update_conversation_context(search_result.movies[0])
    
    # ===== STEP 3: LLM Answer Generation =====
    final_answer = _generate_answer_with_llm(
        question=question,
        intent_analysis=intent_analysis,
        search_result=search_result,
        conversation_history=conversation_history
    )
    
    return final_answer, search_result.movies, search_result.source


def _analyze_intent_with_llm(
    question: str,
    conversation_history: List[Dict[str, str]]
) -> Optional[Dict]:
    """
    Step 1: LLM analyzes user intent and extracts search parameters
    """
    try:
        llm = get_llm_client()
        
        # Build conversation context
        history_str = _build_history_string(conversation_history)
        
        # Enhanced classification prompt
        classification = llm.classify_query_enhanced(
            query=question,
            history=history_str
        )
        
        # Map to QueryIntent enum
        intent_str = classification.get('query_type', 'general_info')
        intent = _map_to_intent_enum(intent_str)
        
        # Extract movie entity (handle context resolution)
        movie_entity = classification.get('movie_title')
        needs_context = classification.get('needs_context', False)
        
        if needs_context and not movie_entity and _last_discussed_movie:
            movie_entity = _last_discussed_movie
            logger.info(f"🔗 Using context: {movie_entity}")
        
        # Detect language
        language = _detect_language(question)
        
        return {
            'intent': intent,
            'movie_entity': movie_entity,
            'genre': classification.get('genre'),
            'needs_context': needs_context,
            'language': language,
            'specific_field': intent_str,
            'search_query': classification.get('search_query', question),
            'specific_entity': classification.get('specific_entity')
        }
        
    except Exception as e:
        logger.error(f"❌ Intent analysis error: {e}", exc_info=True)
        return None


def _execute_targeted_search(intent_analysis: Dict) -> Optional[SearchResult]:
    """Step 2: Execute targeted search with fallback chain"""
    intent = intent_analysis['intent']
    movie_entity = intent_analysis.get('movie_entity')
    genre = intent_analysis.get('genre')
    
    # Build search query based on intent
    search_query = _build_search_query(intent_analysis)
    
    logger.info(f"🔍 Targeted search: query='{search_query}', intent={intent}")
    
    # ===== Try 1: FAISS Search =====
    movies, source = _search_faiss(search_query, intent)
    
    if movies:
        logger.info(f"✅ FAISS hit: {len(movies)} results")
        return SearchResult(movies=movies, source=source, intent=intent)
    
    # ===== Try 2: PostgreSQL Direct Query =====
    movies, source = _search_postgresql_direct(search_query, intent_analysis)
    
    if movies:
        logger.info(f"✅ PostgreSQL hit: {len(movies)} results")
        _store_in_faiss_async(movies)
        return SearchResult(movies=movies, source=source, intent=intent)
    
    # ===== Try 3: TMDb API Fallback =====
    movies = _search_and_store_from_tmdb(search_query, intent_analysis)
    
    if movies:
        logger.info(f"✅ TMDb hit: {len(movies)} results")
        return SearchResult(movies=movies, source="tmdb_api", intent=intent)
    
    logger.warning("⚠️ No results from any source")
    return None


def _build_search_query(intent_analysis: Dict) -> str:
    """Build optimized search query based on intent"""
    intent = intent_analysis['intent']
    movie_entity = intent_analysis.get('movie_entity')
    genre = intent_analysis.get('genre')
    search_query = intent_analysis.get('search_query', '')
    specific_entity = intent_analysis.get('specific_entity')
    
    if intent == QueryIntent.ENTITY_SEARCH and specific_entity:
        return specific_entity
    
    if intent == QueryIntent.RECOMMENDATION:
        if genre:
            return genre
        return "popular movies"
    
    if movie_entity:
        return movie_entity
    
    return search_query


def _search_faiss(search_query: str, intent: QueryIntent) -> Tuple[List[Dict], str]:
    """Search using FAISS vector database"""
    try:
        orchestrator = get_search_orchestrator()
        
        # Determine limit based on intent
        if intent == QueryIntent.RECOMMENDATION:
            limit = 10
        elif intent == QueryIntent.FRANCHISE:  # ← ADD THIS
            limit = 20  # Get more results for franchise search
        else:
            limit = 5
        
        # Use hybrid search (FAISS + metadata filtering)
        movies, source = orchestrator.search_hybrid(
            query=search_query,
            limit=limit
        )
        
        if movies:
            # Enrich if needed
            movies = [_enrich_if_needed(m) for m in movies]
            return movies, source
        
        return [], "none"
        
    except Exception as e:
        logger.error(f"❌ FAISS search error: {e}")
        return [], "none"


def _search_postgresql_direct(search_query: str, intent_analysis: Dict) -> Tuple[List[Dict], str]:
    """Direct PostgreSQL query"""
    try:
        orchestrator = get_search_orchestrator()
        movies = orchestrator.search_postgresql_by_intent(
            query=search_query,
            intent=intent_analysis['intent'].value,
            limit=10
        )
        
        if movies:
            movies = [_enrich_if_needed(m) for m in movies]
            return movies, "postgresql"
        
        return [], "none"
        
    except Exception as e:
        logger.error(f"❌ PostgreSQL search error: {e}")
        return [], "none"


def _search_and_store_from_tmdb(search_query: str, intent_analysis: Dict) -> List[Dict]:
    """Search TMDb API and store results"""
    try:
        tmdb = get_tmdb_client()
        orchestrator = get_search_orchestrator()
        
        results = tmdb.search_movies(search_query)
        
        if not results or 'results' not in results or len(results['results']) == 0:
            return []
        
        movies = []
        
        for movie_data in results['results'][:5]:
            tmdb_id = movie_data['id']
            
            existing = get_movie_by_tmdb_id(tmdb_id)
            if existing:
                movies.append(existing)
                continue
            
            enriched_movie = _fetch_full_tmdb_details(tmdb_id, movie_data)
            
            if enriched_movie:
                stored_movie = orchestrator.store_movie_to_db(enriched_movie)
                
                if stored_movie:
                    _store_in_faiss_async([stored_movie])
                    movies.append(stored_movie)
        
        return movies
        
    except Exception as e:
        logger.error(f"❌ TMDb search error: {e}", exc_info=True)
        return []


def _generate_answer_with_llm(
    question: str,
    intent_analysis: Dict,
    search_result: SearchResult,
    conversation_history: List[Dict[str, str]]
) -> str:
    """Step 3: LLM generates natural language answer"""
    try:
        llm = get_llm_client()
        
        if not search_result.movies or len(search_result.movies) == 0:
            logger.warning("⚠️ No movies in search result")
            return _generate_no_result_response(question, intent_analysis)
        
        # ✅ Handle franchise queries differently
        if intent_analysis['intent'] == QueryIntent.FRANCHISE:
            # Send ALL movies for franchise questions
            movie_context = _format_franchise_context(search_result.movies)
        else:
            # Send only first movie for other queries
            movie = search_result.movies[0]
            movie_context = _format_movie_context(movie, intent_analysis['intent'])
        
        # Generate answer using LLM
        answer = llm.generate_answer(
            question=question,
            intent=intent_analysis['specific_field'],
            movie_data=movie_context,
            language=intent_analysis['language'],
            conversation_history=conversation_history[-3:]
        )
        
        logger.info(f"✅ Generated answer: {len(answer)} chars")
        return answer
        
    except Exception as e:
        logger.error(f"❌ Answer generation error: {e}", exc_info=True)
        
        # Fallback
        try:
            if search_result and search_result.movies and len(search_result.movies) > 0:
                # ✅ Handle franchise fallback
                if intent_analysis['intent'] == QueryIntent.FRANCHISE:
                    return _generate_franchise_answer(
                        movies=search_result.movies,
                        is_indonesian=(intent_analysis['language'] == 'id')
                    )
                else:
                    return _generate_rule_based_answer(
                        movie=search_result.movies[0],
                        query_type=intent_analysis['specific_field'],
                        is_indonesian=(intent_analysis['language'] == 'id'),
                        is_recommendation=(intent_analysis['intent'] == QueryIntent.RECOMMENDATION),
                        question=question
                    )
            else:
                logger.warning("⚠️ No movies available for fallback")
                return _generate_no_result_response(question, intent_analysis)
        except Exception as fallback_error:
            logger.error(f"❌ Fallback error: {fallback_error}", exc_info=True)
            return _generate_fallback_response(question)

# ===== Helper Functions =====

def _map_to_intent_enum(intent_str: str) -> QueryIntent:
    """Map string intent to enum"""
    mapping = {
        'cast': QueryIntent.CAST,
        'director': QueryIntent.DIRECTOR,
        'plot': QueryIntent.PLOT,
        'year': QueryIntent.YEAR,
        'rating': QueryIntent.RATING,
        'genre': QueryIntent.GENRE,
        'runtime': QueryIntent.RUNTIME,
        'location': QueryIntent.LOCATION,
        'franchise': QueryIntent.FRANCHISE,  # ← ADD THIS
        'recommendation': QueryIntent.RECOMMENDATION,
        'general_info': QueryIntent.GENERAL_INFO,
        'movie_info': QueryIntent.MOVIE_INFO,
        'entity_search': QueryIntent.ENTITY_SEARCH
    }
    return mapping.get(intent_str, QueryIntent.UNKNOWN)


def _enrich_if_needed(movie: Dict) -> Dict:
    """Enrich movie data if incomplete"""
    if _needs_enrichment(movie):
        enriched = _enrich_from_tmdb(movie)
        return enriched if enriched else movie
    return movie


def _needs_enrichment(movie: Dict) -> bool:
    """Check if movie needs enrichment"""
    overview = movie.get('overview', '')
    cast = movie.get('cast', [])
    directors = movie.get('directors', [])
    return not overview or len(cast) == 0 or len(directors) == 0


def _enrich_from_tmdb(movie: Dict) -> Optional[Dict]:
    """Enrich movie from TMDb API"""
    try:
        tmdb_id = movie.get('tmdb_id')
        if not tmdb_id:
            return None
        
        tmdb = get_tmdb_client()
        details = tmdb.get_movie_details(tmdb_id)
        credits = tmdb.get_movie_credits(tmdb_id)
        
        if not details:
            return None
        
        directors = []
        if credits and 'crew' in credits:
            directors = [c['name'] for c in credits['crew'] if c.get('job') == 'Director']
        
        cast = []
        if credits and 'cast' in credits:
            cast = [c['name'] for c in credits['cast'][:15]]
        
        genres_list = []
        if 'genres' in details:
            genres_list = [g['name'] for g in details['genres']]
        
        enriched = movie.copy()
        enriched.update({
            'overview': details.get('overview', movie.get('overview', '')),
            'directors': directors or movie.get('directors', []),
            'cast': cast or movie.get('cast', []),
            'genres_csv': ', '.join(genres_list) if genres_list else movie.get('genres_csv', ''),
            'vote_average': details.get('vote_average', movie.get('vote_average', 0)),
            'runtime': details.get('runtime', movie.get('runtime', 0))
        })
        
        return enriched
        
    except Exception as e:
        logger.error(f"❌ Enrichment error: {e}")
        return None


def _fetch_full_tmdb_details(tmdb_id: int, movie_data: Dict) -> Optional[Dict]:
    """Fetch complete movie details from TMDb"""
    try:
        tmdb = get_tmdb_client()
        
        details = tmdb.get_movie_details(tmdb_id)
        credits = tmdb.get_movie_credits(tmdb_id)
        
        if not details:
            return None
        
        year = None
        if 'release_date' in details and details['release_date']:
            try:
                year = int(details['release_date'][:4])
            except:
                pass
        
        genres_list = [g['name'] for g in details.get('genres', [])]
        
        directors = []
        if credits and 'crew' in credits:
            directors = [c['name'] for c in credits['crew'] if c.get('job') == 'Director']
        
        cast = []
        if credits and 'cast' in credits:
            cast = [c['name'] for c in credits['cast'][:15]]
        
        return {
            'tmdb_id': tmdb_id,
            'title': details.get('title', movie_data.get('title', 'Unknown')),
            'year': year,
            'overview': details.get('overview', ''),
            'popularity': details.get('popularity', 0),
            'vote_average': details.get('vote_average', 0),
            'genres_csv': ', '.join(genres_list),
            'directors': directors,
            'cast': cast,
            'runtime': details.get('runtime', 0)
        }
        
    except Exception as e:
        logger.error(f"❌ TMDb fetch error: {e}")
        return None


def _store_in_faiss_async(movies: List[Dict]):
    """Store movies in FAISS asynchronously"""
    try:
        orchestrator = get_search_orchestrator()
        orchestrator.add_movies_to_faiss(movies)
        logger.info(f"✅ Added {len(movies)} movies to FAISS")
    except Exception as e:
        logger.error(f"❌ FAISS storage error: {e}")


def _format_movie_context(movie: Dict, intent: QueryIntent) -> Dict:
    """Format movie data for LLM consumption"""
    return {
        'title': movie.get('title', 'Unknown'),
        'year': movie.get('year', ''),
        'overview': movie.get('overview', ''),
        'directors': movie.get('directors', []),
        'cast': movie.get('cast', []),
        'rating': movie.get('vote_average', 0),
        'genres': movie.get('genres_csv', ''),
        'runtime': movie.get('runtime', 0)
    }

def _format_franchise_context(movies: List[Dict]) -> Dict:
    """Format multiple movies for franchise questions"""
    movie_list = []
    for movie in movies[:20]:  # Limit to 20 movies
        movie_list.append({
            'title': movie.get('title', 'Unknown'),
            'year': movie.get('year', ''),
            'rating': movie.get('vote_average', 0)
        })
    
    return {
        'franchise_movies': movie_list,
        'total_count': len(movie_list)
    }


def _generate_franchise_answer(movies: List[Dict], is_indonesian: bool) -> str:
    """Generate franchise listing answer (fallback)"""
    if not movies:
        return "Tidak ada film yang ditemukan." if is_indonesian else "No movies found."
    
    # Group by title (remove year variations)
    unique_titles = {}
    for movie in movies:
        title = movie.get('title', 'Unknown')
        year = movie.get('year', '')
        if title not in unique_titles:
            unique_titles[title] = {'title': title, 'year': year}
    
    movie_list = list(unique_titles.values())
    count = len(movie_list)
    
    if is_indonesian:
        answer = f"Ada {count} film yang ditemukan:\n"
        for i, movie in enumerate(movie_list[:20], 1):
            year_str = f" ({movie['year']})" if movie['year'] else ""
            answer += f"{i}. {movie['title']}{year_str}\n"
    else:
        answer = f"There are {count} movies found:\n"
        for i, movie in enumerate(movie_list[:20], 1):
            year_str = f" ({movie['year']})" if movie['year'] else ""
            answer += f"{i}. {movie['title']}{year_str}\n"
    
    return answer.strip()

def _update_conversation_context(movie: Dict):
    """Update global conversation context"""
    global _last_discussed_movie
    
    title = movie.get('title', 'Unknown')
    year = movie.get('year', '')
    _last_discussed_movie = f"{title} ({year})" if year else title
    
    logger.info(f"💾 Context updated: {_last_discussed_movie}")


def _build_history_string(conversation_history: List[Dict[str, str]]) -> str:
    """Build conversation history string for LLM"""
    history_str = ""
    for msg in conversation_history[-3:]:
        role = msg.get('role', 'user')
        content = msg.get('content', '')
        history_str += f"{role}: {content}\n"
    return history_str


def _detect_language(text: str) -> str:
    """Detect language (ID/EN)"""
    text_lower = text.lower()
    
    indonesian_keywords = {
        'siapa', 'apa', 'kapan', 'dimana', 'bagaimana', 'mengapa', 'kenapa',
        'berapa', 'filmnya', 'sutradara', 'pemain', 'pemeran', 'tentang',
        'dirilis', 'dibuat', 'yang', 'dari', 'untuk', 'dengan', 'dan',
        'rekomendasikan', 'berikan', 'carikan', 'cerita', 'deskripsi'
    }
    
    english_keywords = {
        'who', 'what', 'when', 'where', 'how', 'why', 'which',
        'the', 'movie', 'cast', 'director', 'about', 'released', 'made',
        'recommend', 'suggest', 'give', 'description', 'plot', 'story'
    }
    
    words = text_lower.split()
    id_count = sum(1 for w in words if w in indonesian_keywords)
    en_count = sum(1 for w in words if w in english_keywords)
    
    return 'id' if id_count > en_count else 'en'


def _generate_fallback_response(question: str) -> str:
    """Generate fallback response when intent analysis fails"""
    lang = _detect_language(question)
    if lang == 'id':
        return "Maaf, saya tidak dapat memahami pertanyaan Anda. Bisakah Anda mengulanginya dengan lebih jelas?"
    else:
        return "I'm sorry, I couldn't understand your question. Could you rephrase it?"


def _generate_no_result_response(question: str, intent_analysis: Dict) -> str:
    """Generate response when no results found"""
    lang = intent_analysis.get('language', 'en')
    if lang == 'id':
        return "Maaf, saya tidak dapat menemukan informasi yang Anda cari. Silakan coba dengan kata kunci lain."
    else:
        return "I couldn't find any information. Please try different keywords."


def _generate_rule_based_answer(movie: Dict, query_type: str, is_indonesian: bool, is_recommendation: bool, question: str = "") -> str:
    """Legacy rule-based answer generation (fallback)"""
    title = movie.get('title', 'Unknown')
    year = movie.get('year', '')
    year_str = f" ({year})" if year else ""
    overview = movie.get('overview', '')
    directors = movie.get('directors', [])
    cast = movie.get('cast', [])
    rating = movie.get('vote_average', 0)
    genres = movie.get('genres_csv', '')
    
    # LOCATION (filming location not available)
    if query_type == 'location':
        if is_indonesian:
            return f"Maaf, saya tidak memiliki informasi tentang lokasi pengambilan gambar untuk film {title}{year_str}. Saya dapat memberikan informasi tentang sinopsis, pemain, sutradara, tahun rilis, atau rating film. Apakah Anda ingin mengetahui salah satunya?"
        else:
            return f"I'm sorry, I don't have information about where {title}{year_str} was filmed. However, I can provide information about the plot, cast, director, release year, or rating. Would you like to know about any of these?"
    
    # PLOT ONLY (no title/year in answer)
    elif query_type == 'plot':
        if overview:
            return overview
        else:
            return f"Maaf, saya tidak memiliki deskripsi untuk {title}{year_str}." if is_indonesian else f"I don't have a description for {title}{year_str}."
    
    # CAST
    elif query_type == 'cast':
        if cast:
            cast_list = ', '.join(cast[:8])
            if len(cast) > 8:
                cast_list += f", dan {len(cast) - 8} lainnya" if is_indonesian else f", and {len(cast) - 8} more"
            
            return f"Pemain dalam film {title}{year_str} meliputi: {cast_list}." if is_indonesian else f"The cast of {title}{year_str} includes {cast_list}."
        else:
            return f"Maaf, saya tidak memiliki informasi pemain untuk {title}{year_str}." if is_indonesian else f"I don't have cast information for {title}{year_str}."
    
    # DIRECTOR
    elif query_type == 'director':
        if directors:
            director_list = ', '.join(directors[:3])
            return f"Film {title}{year_str} disutradarai oleh {director_list}." if is_indonesian else f"{title}{year_str} was directed by {director_list}."
        else:
            return f"Maaf, saya tidak memiliki informasi sutradara untuk {title}{year_str}." if is_indonesian else f"I don't have director information for {title}{year_str}."
    
    # YEAR
    elif query_type == 'year':
        if year:
            return f"Film {title} dirilis pada tahun {year}." if is_indonesian else f"{title} was released in {year}."
        else:
            return f"Maaf, saya tidak memiliki informasi tahun rilis untuk {title}." if is_indonesian else f"I don't have release year information for {title}."
    
    # RATING
    elif query_type == 'rating':
        if rating > 0:
            return f"Film {title}{year_str} memiliki rating {rating}/10." if is_indonesian else f"{title}{year_str} has a rating of {rating}/10."
        else:
            return f"Maaf, saya tidak memiliki informasi rating untuk {title}{year_str}." if is_indonesian else f"I don't have rating information for {title}{year_str}."
    
    # GENERAL MOVIE INFO (Title + Year + Description)
    else:
        parts = []
        parts.append(f"{title}{year_str}")
        
        if overview:
            ov_text = overview[:400] + "..." if len(overview) > 400 else overview
            parts.append(ov_text)
        else:
            if is_indonesian:
                parts.append("Deskripsi tidak tersedia.")
            else:
                parts.append("Description not available.")
        
        return ' '.join(parts)


# Legacy wrapper
def answer_question_with_context(
    question: str,
    conversation_history: Optional[List[Dict[str, str]]] = None
) -> Tuple[str, List[Dict], str]:
    """Legacy wrapper for backward compatibility"""
    return answer_question_with_llm(question, conversation_history)