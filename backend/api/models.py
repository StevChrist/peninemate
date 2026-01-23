from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class QuestionRequest(BaseModel):
    question: str
    conversation_history: Optional[List[Dict[str, str]]] = []

class MovieResponse(BaseModel):
    tmdb_id: int
    title: str
    year: Optional[int] = None
    overview: Optional[str] = None
    popularity: Optional[float] = None
    box_office_worldwide: Optional[float] = None
    box_office_domestic: Optional[float] = None
    box_office_foreign: Optional[float] = None

class QAResponse(BaseModel):
    answer: str
    movies: List[MovieResponse] = []
    source: Optional[str] = None
    search_method: Optional[str] = None

class SearchResponse(BaseModel):
    results: List[MovieResponse]
    total: int
    source: str

class CreditPerson(BaseModel):
    name: str
    character: Optional[str] = None
    job: Optional[str] = None

class MovieDetailResponse(MovieResponse):
    directors: List[str] = []
    cast: List[CreditPerson] = []

class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    database: Dict[str, Any]
    cache: Dict[str, Any]
    faiss: Dict[str, Any]

class StatsResponse(BaseModel):
    database_stats: Dict[str, Any]
    cache_stats: Dict[str, Any]
    faiss_stats: Dict[str, Any]

class RecommendationRequest(BaseModel):
    genres: List[str] = []
    mood: List[str] = []
    theme: List[str] = []
    storyline: List[str] = []
    year: List[str] = []
    duration: List[str] = []
    durationComparison: str = "exact"  # "over" | "less" | "exact"
    exclude: List[str] = []  # List of movie titles to exclude

class RecommendationResponse(BaseModel):
    title: str
    genre: str
    duration: int
    cast: List[str]
    rating: float
    region: str
    overview: Optional[str] = None
