# peninemate/infrastructure/tmdb_client.py
"""TMDb API Client"""

import os
import requests
import logging
from typing import Dict, Optional, List

logger = logging.getLogger(__name__)


class TMDbClient:
    """Client for TMDb API"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('TMDB_API_KEY')
        self.base_url = 'https://api.themoviedb.org/3'
        
        if not self.api_key:
            logger.warning("⚠️ TMDB_API_KEY not found in environment")
    
    def search_movies(self, query: str, page: int = 1) -> Optional[Dict]:
        """
        Search movies by query
        
        Args:
            query: Search query
            page: Page number
        
        Returns:
            Dict with 'results' list of movies
        """
        if not self.api_key:
            return None
        
        try:
            response = requests.get(
                f'{self.base_url}/search/movie',
                params={
                    'api_key': self.api_key,
                    'query': query,
                    'page': page,
                    'language': 'en-US'
                },
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"TMDb search failed: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"TMDb search error: {e}")
            return None
    
    def get_movie_details(self, tmdb_id: int) -> Optional[Dict]:
        """Get detailed movie information"""
        if not self.api_key:
            return None
        
        try:
            response = requests.get(
                f'{self.base_url}/movie/{tmdb_id}',
                params={'api_key': self.api_key},
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            return None
            
        except Exception as e:
            logger.error(f"TMDb details error: {e}")
            return None
    
    def get_movie_credits(self, tmdb_id: int) -> Optional[Dict]:
        """Get movie credits (cast + crew)"""
        if not self.api_key:
            return None
        
        try:
            response = requests.get(
                f'{self.base_url}/movie/{tmdb_id}/credits',
                params={'api_key': self.api_key},
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            return None
            
        except Exception as e:
            logger.error(f"TMDb credits error: {e}")
            return None
    
    # ✅ NEW METHOD: Discover movies with filters
    def discover_movies(self, **params) -> Optional[List[Dict]]:
        """
        Discover movies with filters
        
        Args:
            **params: Query parameters like:
                - sort_by: e.g., "popularity.desc"
                - with_genres: comma-separated genre IDs
                - primary_release_year: year filter
                - page: page number
        
        Returns:
            List of movies or None
        """
        if not self.api_key:
            return None
        
        try:
            response = requests.get(
                f'{self.base_url}/discover/movie',
                params={
                    'api_key': self.api_key,
                    'language': 'en-US',
                    **params
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get('results', [])
            else:
                logger.error(f"TMDb discover failed: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"TMDb discover error: {e}")
            return None


# Singleton
_tmdb_client = None

def get_tmdb_client() -> TMDbClient:
    """Get singleton TMDb client"""
    global _tmdb_client
    if _tmdb_client is None:
        _tmdb_client = TMDbClient()
    return _tmdb_client
