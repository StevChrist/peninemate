"""
TMDb API Client with caching
"""
import os
import requests
from peninemate.infrastructure.cache_client import get_cache

class TMDbClient:
    """TMDb API Client with cache support"""
    
    def __init__(self):
        self.api_key = os.getenv("TMDB_API_KEY")
        self.base_url = "https://api.themoviedb.org/3"
        self.cache = get_cache()
    
    def get_movie_details(self, movie_id: int):
        """
        Get movie details with credits
        Uses cache to reduce API calls
        
        Args:
            movie_id: TMDb movie ID
        
        Returns:
            Movie details dict or None
        """
        # Try cache first
        cache_key = f"movie:{movie_id}"
        cached = self.cache.get(cache_key)
        if cached:
            print(f" ✅ Cache hit: movie {movie_id}")
            return cached
        
        # Cache miss - fetch from API
        print(f" 📡 Cache miss: fetching movie {movie_id} from TMDb API")
        try:
            url = f"{self.base_url}/movie/{movie_id}"
            params = {
                "api_key": self.api_key,
                "append_to_response": "credits"
            }
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                # Store in cache (1 hour TTL)
                self.cache.set(cache_key, data, ttl=3600)
                return data
            else:
                return None
        except Exception as e:
            print(f"TMDb API error: {e}")
            return None
    
    def search_movie(self, query: str, year: int = None):
        """
        Search movies by title
        Uses cache for search results
        
        Args:
            query: Movie title
            year: Release year (optional)
        
        Returns:
            List of movie results
        """
        # Create cache key including year
        cache_key = f"search:{query.lower()}"
        if year:
            cache_key += f":{year}"
        
        # Try cache
        cached = self.cache.get(cache_key)
        if cached:
            print(f" ✅ Cache hit: search '{query}'")
            return cached
        
        # Cache miss
        print(f" 📡 Cache miss: searching '{query}' on TMDb API")
        try:
            url = f"{self.base_url}/search/movie"
            params = {
                "api_key": self.api_key,
                "query": query
            }
            
            if year:
                params["year"] = year
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                # Store in cache (shorter TTL for search: 30 min)
                self.cache.set(cache_key, results, ttl=1800)
                return results
            else:
                return []
        except Exception as e:
            print(f"TMDb API error: {e}")
            return []
    
    def discover_movies(self, **kwargs):
        """
        Discover movies with filters
        
        Args:
            **kwargs: Query parameters (sort_by, with_genres, primary_release_year, etc.)
        
        Returns:
            List of movie dictionaries
        """
        url = f"{self.base_url}/discover/movie"
        params = {**kwargs, "api_key": self.api_key}
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get('results', [])
        except Exception as e:
            print(f"TMDb discover error: {e}")
            return []
    
    def get_movie_credits(self, movie_id: int):
        """
        Get movie credits (cast and crew)
        
        Args:
            movie_id: TMDb movie ID
        
        Returns:
            Dict with credits or None
        """
        # Try cache first
        cache_key = f"credits:{movie_id}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        try:
            url = f"{self.base_url}/movie/{movie_id}/credits"
            params = {"api_key": self.api_key}
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                self.cache.set(cache_key, data, ttl=3600)
                return data
            else:
                return None
        except Exception as e:
            print(f"TMDb get movie credits error: {e}")
            return None
    
    def get_cache_stats(self):
        """Get cache statistics"""
        return self.cache.get_stats()


# Singleton
_client = None

def get_tmdb_client():
    """Get TMDb client instance"""
    global _client
    if _client is None:
        _client = TMDbClient()
    return _client
