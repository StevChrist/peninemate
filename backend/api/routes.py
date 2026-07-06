# api/routes.py
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, Tuple
import logging
from datetime import datetime, timezone, timedelta
import threading

from .models import (
    QuestionRequest, QAResponse, SearchResponse, MovieDetailResponse,
    HealthResponse, StatsResponse, MovieResponse, CreditPerson,
    RecommendationResponse, RecommendationRequest
)

from peninemate.core_logic.qa_service import answer_question_with_context, answer_question_with_llm
from peninemate.core_logic.search_orchestrator import get_search_orchestrator
from peninemate.core_logic.qa_db import get_movie_by_tmdb_id, get_credits_for_movie
from peninemate.infrastructure.db_client import get_conn
from peninemate.infrastructure.cache_client import get_cache

logger = logging.getLogger(__name__)

class GlobalChatRateLimiter:
    def __init__(self, limit: int = 100):
        self.limit = limit
        self.lock = threading.Lock()
        self.count = 0
        self.reset_date = None # YYYY-MM-DD
        
    def check_limit(self) -> Tuple[bool, str]:
        tz_wib = timezone(timedelta(hours=7))
        now_wib = datetime.now(tz_wib)
        current_date_str = now_wib.strftime("%Y-%m-%d")
        
        tomorrow_wib = (now_wib + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        months_id = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
        reset_time_str = f"{tomorrow_wib.day} {months_id[tomorrow_wib.month - 1]} {tomorrow_wib.year} pukul 00:00 WIB"
        
        with self.lock:
            if self.reset_date != current_date_str:
                self.count = 0
                self.reset_date = current_date_str
                
            if self.count >= self.limit:
                return False, reset_time_str
                
            self.count += 1
            return True, reset_time_str

chat_limiter = GlobalChatRateLimiter(limit=100)

router = APIRouter(prefix="/api/v1")

@router.get("/chat-limit")
async def get_chat_limit():
    from datetime import datetime, timezone, timedelta
    tz_wib = timezone(timedelta(hours=7))
    now_wib = datetime.now(tz_wib)
    current_date_str = now_wib.strftime("%Y-%m-%d")
    
    tomorrow_wib = (now_wib + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    months_id = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
    reset_time_str = f"{tomorrow_wib.day} {months_id[tomorrow_wib.month - 1]} {tomorrow_wib.year} pukul 00:00 WIB"
    
    with chat_limiter.lock:
        if chat_limiter.reset_date != current_date_str:
            chat_limiter.count = 0
            chat_limiter.reset_date = current_date_str
            
        remaining = max(0, chat_limiter.limit - chat_limiter.count)
        return {
            "remaining_chats": remaining,
            "max_chats": chat_limiter.limit,
            "reset_time": reset_time_str
        }

# ============================================================================
# Q&A ENDPOINT
# ============================================================================

@router.post("/qa", response_model=QAResponse)
async def qa_endpoint(request: QuestionRequest):
    """
    Main Q&A endpoint - answers questions about movies
    
    Request body:
    - question: User's question (required)
    - conversation_history: List of previous messages (optional)
    
    Response:
    - answer: Natural language answer
    - movies: List of relevant movies
    - source: Data source (keyword/semantic/api/hybrid)
    """
    try:
        logger.info(f"📝 Q&A request: {request.question}")
        
        # Check daily chat limit
        is_allowed, reset_time_str = chat_limiter.check_limit()
        if not is_allowed:
            limit_message = (
                f"Maaf, limit chat harian global (100 chat) telah habis. "
                f"Anda hanya dapat menggunakan fitur Recommendation untuk saat ini. "
                f"Limit akan di-reset pada {reset_time_str}."
            )
            logger.warning("🚫 Daily global chat limit reached. Limit message returned.")
            return QAResponse(
                answer=limit_message,
                movies=[],
                source="limit_reached",
                search_method="none",
                remaining_chats=0,
                max_chats=chat_limiter.limit,
                reset_time=reset_time_str
            )
            
        logger.info(f"📚 History length: {len(request.conversation_history)} messages")
        
        # Use answer_question_with_llm (OpenAI)
        answer, movies, source = answer_question_with_llm(
            question=request.question,
            conversation_history=request.conversation_history
        )
        
        logger.info(f"✅ Answer generated: {answer[:100]}...")
        logger.info(f"📊 Movies returned: {len(movies)}")
        logger.info(f"🔍 Source: {source}")
        
        # Convert movies to MovieResponse format
        movie_responses = []
        if movies:
            for movie in movies:
                try:
                    if not movie.get('tmdb_id'):
                        logger.warning(f"⚠️ Movie without tmdb_id: {movie}")
                        continue
                    
                    movie_responses.append(MovieResponse(
                        tmdb_id=movie.get('tmdb_id'),
                        title=movie.get('title', 'Unknown'),
                        year=movie.get('year'),
                        overview=movie.get('overview'),
                        popularity=movie.get('popularity'),
                        box_office_worldwide=movie.get('box_office_worldwide'),
                        box_office_domestic=movie.get('box_office_domestic'),
                        box_office_foreign=movie.get('box_office_foreign')
                    ))
                except Exception as e:
                    logger.warning(f"⚠️ Error converting movie: {e}")
                    continue
        
        return QAResponse(
            answer=answer,
            movies=movie_responses,
            source=source,
            search_method=source,
            remaining_chats=max(0, chat_limiter.limit - chat_limiter.count),
            max_chats=chat_limiter.limit,
            reset_time=reset_time_str
        )
    
    except Exception as e:
        logger.error(f"❌ Error in Q&A endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# SEARCH ENDPOINT
# ============================================================================

@router.get("/movies/search", response_model=SearchResponse)
async def search_movies(
    q: str = Query(..., description="Search query"),
    year: Optional[int] = Query(None, description="Filter by release year"),
    limit: int = Query(5, ge=1, le=20, description="Maximum number of results")
):
    """
    Search movies by title or description
    
    Query params:
    - q: Search query (title, description, or keywords)
    - year: Optional release year filter
    - limit: Max results (1-20, default 5)
    
    Response:
    - results: List of matching movies
    - total: Number of results
    - source: Search method used
    """
    try:
        logger.info(f"🔍 Search request: q='{q}', year={year}, limit={limit}")
        
        orchestrator = get_search_orchestrator()
        movies, source = orchestrator.search_hybrid(q, limit=limit)
        
        # Filter by year if provided
        if year and movies:
            movies = [m for m in movies if m.get('year') == year]
            logger.info(f"🎯 Filtered by year {year}: {len(movies)} results")
        
        # Convert to MovieResponse format
        movie_responses = []
        if movies:
            for m in movies:
                try:
                    if not m.get('tmdb_id'):
                        continue
                    
                    movie_responses.append(MovieResponse(
                        tmdb_id=m.get('tmdb_id'),
                        title=m.get('title', 'Unknown'),
                        year=m.get('year'),
                        overview=m.get('overview'),
                        popularity=m.get('popularity'),
                        box_office_worldwide=m.get('box_office_worldwide'),
                        box_office_domestic=m.get('box_office_domestic'),
                        box_office_foreign=m.get('box_office_foreign')
                    ))
                except Exception as e:
                    logger.warning(f"⚠️ Error converting movie: {e}")
                    continue
        
        logger.info(f"✅ Search completed: {len(movie_responses)} results from {source}")
        
        return SearchResponse(
            results=movie_responses,
            total=len(movie_responses),
            source=source
        )
    
    except Exception as e:
        logger.error(f"❌ Error in search endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# MOVIE DETAILS ENDPOINT
# ============================================================================

@router.get("/movies/{tmdb_id}", response_model=MovieDetailResponse)
async def get_movie_details(tmdb_id: int):
    """
    Get detailed movie information including credits
    
    Path params:
    - tmdb_id: TMDb movie ID
    
    Response:
    - Movie details with directors and cast
    """
    try:
        logger.info(f"🎬 Movie details request: tmdb_id={tmdb_id}")
        
        # Get movie from database
        movie = get_movie_by_tmdb_id(tmdb_id)
        
        if not movie:
            logger.warning(f"⚠️ Movie not found: tmdb_id={tmdb_id}")
            raise HTTPException(
                status_code=404,
                detail=f"Movie with tmdb_id {tmdb_id} not found"
            )
        
        # Get credits
        credits = get_credits_for_movie(tmdb_id)
        
        directors = []
        cast_list = []
        
        if credits:
            for credit in credits:
                try:
                    if credit['credit_type'] == 'crew' and credit.get('job') == 'Director':
                        directors.append(credit['person_name'])
                    elif credit['credit_type'] == 'cast':
                        cast_list.append(CreditPerson(
                            name=credit['person_name'],
                            character=credit.get('character_name')
                        ))
                except Exception as e:
                    logger.warning(f"⚠️ Error processing credit: {e}")
                    continue
        
        logger.info(f"✅ Movie details: {movie['title']} ({movie.get('year')}) - {len(directors)} directors, {len(cast_list)} cast")
        
        return MovieDetailResponse(
            tmdb_id=movie['tmdb_id'],
            title=movie['title'],
            year=movie.get('year'),
            overview=movie.get('overview'),
            popularity=movie.get('popularity'),
            box_office_worldwide=movie.get('box_office_worldwide'),
            box_office_domestic=movie.get('box_office_domestic'),
            box_office_foreign=movie.get('box_office_foreign'),
            directors=directors,
            cast=cast_list[:10]  # Return top 10 cast
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in movie details endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# RECOMMENDATION ENDPOINT
# ============================================================================

@router.post("/recommend", response_model=RecommendationResponse)
async def recommend_movie_endpoint(request: RecommendationRequest):
    """
    Movie recommendation endpoint based on user preferences
    
    Request body:
    - genres: List of genres
    - mood: List of moods
    - theme: List of themes
    - storyline: List of storyline elements
    - year: List of year ranges
    - duration: List of duration ranges
    - durationComparison: "over" | "less" | "exact"
    - exclude: List of movie titles to exclude
    
    Response:
    - Recommended movie with details
    """
    try:
        logger.info(f"🎯 Recommendation request received")
        logger.info(f"  Genres: {request.genres}")
        logger.info(f"  Mood: {request.mood}")
        logger.info(f"  Theme: {request.theme}")
        
        from peninemate.core_logic.recommendation_service import recommend_movie
        
        result = recommend_movie(
            genres=request.genres,
            mood=request.mood,
            theme=request.theme,
            storyline=request.storyline,
            year=request.year,
            duration=request.duration,
            duration_comparison=request.durationComparison,
            exclude=request.exclude
        )
        
        if not result:
            logger.warning("⚠️ No recommendation found for criteria")
            return RecommendationResponse(
                title="No recommendation found",
                genre="N/A",
                duration=0,
                cast=[],
                rating=0.0,
                region="N/A",
                overview="Please try different criteria"
            )
        
        logger.info(f"✅ Recommended: {result.get('title')}")
        return RecommendationResponse(**result)
    
    except Exception as e:
        logger.error(f"❌ Error in recommendation endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# HEALTH CHECK ENDPOINT
# ============================================================================

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint - returns system status
    
    Response:
    - status: "ok" | "degraded" | "error"
    - timestamp: Current timestamp
    - database: DB connection status and counts
    - cache: Cache statistics
    - faiss: FAISS index status
    """
    try:
        # Check database
        db_status = {"connected": False, "movies": 0, "credits": 0}
        try:
            conn = get_conn()
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM movies")
            db_status["movies"] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM credits")
            db_status["credits"] = cursor.fetchone()[0]
            
            db_status["connected"] = True
            cursor.close()
            
            logger.info(f"✅ Database: {db_status['movies']} movies, {db_status['credits']} credits")
        except Exception as e:
            logger.error(f"❌ Database health check failed: {str(e)}")
        
        # Check cache
        cache_status = {"size": 0, "hit_rate": "0%"}
        try:
            cache = get_cache()
            stats = cache.get_stats()
            cache_status["size"] = stats.get("size", 0)
            hit_rate = stats.get("hit_rate", 0)
            cache_status["hit_rate"] = hit_rate
            
            logger.info(f"✅ Cache: {cache_status['size']} entries, {cache_status['hit_rate']} hit rate")
        except Exception as e:
            logger.error(f"❌ Cache health check failed: {str(e)}")
        
        # Check FAISS
        faiss_status = {"loaded": False, "vectors": 0}
        try:
            orchestrator = get_search_orchestrator()
            
            if orchestrator.index is not None:
                faiss_status["loaded"] = True
                faiss_status["vectors"] = orchestrator.index.ntotal
            
            logger.info(f"✅ FAISS: {faiss_status['vectors']} vectors loaded")
        except Exception as e:
            logger.error(f"❌ FAISS health check failed: {str(e)}")
        
        # Determine overall status
        overall_status = "ok" if db_status["connected"] and faiss_status["loaded"] else "degraded"
        
        return HealthResponse(
            status=overall_status,
            timestamp=datetime.now(),
            database=db_status,
            cache=cache_status,
            faiss=faiss_status
        )
    
    except Exception as e:
        logger.error(f"❌ Error in health check: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# STATISTICS ENDPOINT
# ============================================================================

@router.get("/stats", response_model=StatsResponse)
async def get_stats():
    """
    System statistics endpoint
    
    Response:
    - database_stats: DB statistics (movies, credits, people)
    - cache_stats: Cache performance metrics
    - faiss_stats: FAISS index information
    """
    try:
        # Database stats
        db_stats = {}
        try:
            conn = get_conn()
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM movies")
            db_stats["total_movies"] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM credits")
            db_stats["total_credits"] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(DISTINCT person_tmdb_person_id) FROM credits")
            db_stats["total_people"] = cursor.fetchone()[0]
            
            cursor.close()
            
            logger.info(f"📊 DB Stats: {db_stats['total_movies']} movies, {db_stats['total_credits']} credits, {db_stats['total_people']} people")
        except Exception as e:
            logger.error(f"❌ Database stats failed: {str(e)}")
            db_stats = {"error": str(e)}
        
        # Cache stats
        cache_stats = {}
        try:
            cache = get_cache()
            cache_stats = cache.get_stats()
            
            logger.info(f"📊 Cache Stats: {cache_stats}")
        except Exception as e:
            logger.error(f"❌ Cache stats failed: {str(e)}")
            cache_stats = {"error": str(e)}
        
        # FAISS stats
        faiss_stats = {}
        try:
            orchestrator = get_search_orchestrator()
            
            faiss_stats = {
                "index_loaded": orchestrator.index is not None,
                "total_vectors": orchestrator.index.ntotal if orchestrator.index else 0,
                "dimension": 384
            }
            
            logger.info(f"📊 FAISS Stats: {faiss_stats['total_vectors']} vectors")
        except Exception as e:
            logger.error(f"❌ FAISS stats failed: {str(e)}")
            faiss_stats = {"error": str(e)}
        
        return StatsResponse(
            database_stats=db_stats,
            cache_stats=cache_stats,
            faiss_stats=faiss_stats
        )
    
    except Exception as e:
        logger.error(f"❌ Error in stats endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# LLM STATUS ENDPOINT (Updated untuk OpenAI)
# ============================================================================

@router.get("/llm/status")
async def llm_status():
    """
    Check LLM (OpenAI) service status
    
    Response:
    - status: "healthy" | "unhealthy" | "error"
    - model: Model name
    - available: Boolean
    - provider: "OpenAI"
    """
    try:
        import os
        from peninemate.infrastructure.llm_client import get_llm_client
        
        api_key = os.getenv("OPENAI_API_KEY")
        
        if not api_key:
            return {
                "status": "error",
                "error": "OPENAI_API_KEY not configured",
                "provider": "OpenAI",
                "model": "gpt-5-nano"
            }
        
        try:
            llm = get_llm_client()
            
            return {
                "status": "healthy",
                "model": "gpt-5-nano",
                "available": True,
                "provider": "OpenAI",
                "api_key_configured": True
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "provider": "OpenAI",
                "model": "gpt-5-nano"
            }
    
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "provider": "OpenAI"
        }