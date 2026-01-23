"""
Simple in-memory cache for TMDb API calls
Using LRU (Least Recently Used) cache with TTL
"""
from functools import lru_cache
from datetime import datetime, timedelta
import threading

class CacheEntry:
    """Cache entry with TTL"""
    def __init__(self, data, ttl_seconds=3600):
        self.data = data
        self.expires_at = datetime.now() + timedelta(seconds=ttl_seconds)
    
    def is_expired(self):
        return datetime.now() > self.expires_at


class SimpleCache:
    """
    Simple in-memory cache with LRU eviction and TTL
    Thread-safe implementation
    """
    def __init__(self, maxsize=1000, default_ttl=3600):
        """
        Args:
            maxsize: Maximum number of items in cache
            default_ttl: Default time-to-live in seconds (1 hour)
        """
        self.cache = {}
        self.maxsize = maxsize
        self.default_ttl = default_ttl
        self.lock = threading.Lock()
        self.hits = 0
        self.misses = 0
    
    def get(self, key: str):
        """
        Get value from cache
        
        Args:
            key: Cache key
        
        Returns:
            Cached value or None if not found/expired
        """
        with self.lock:
            if key in self.cache:
                entry = self.cache[key]
                
                # Check if expired
                if entry.is_expired():
                    del self.cache[key]
                    self.misses += 1
                    return None
                
                # Cache hit
                self.hits += 1
                return entry.data
            
            # Cache miss
            self.misses += 1
            return None
    
    def set(self, key: str, value, ttl: int = None):
        """
        Set value in cache
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (optional)
        """
        with self.lock:
            # LRU eviction if cache is full
            if len(self.cache) >= self.maxsize and key not in self.cache:
                # Remove oldest entry (simple FIFO for now)
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]
            
            # Store with TTL
            ttl = ttl or self.default_ttl
            self.cache[key] = CacheEntry(value, ttl)
    
    def clear(self):
        """Clear all cache"""
        with self.lock:
            self.cache.clear()
            self.hits = 0
            self.misses = 0
    
    def get_stats(self):
        """Get cache statistics"""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0
        
        return {
            'size': len(self.cache),
            'maxsize': self.maxsize,
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': f"{hit_rate:.2f}%"
        }


# Global cache instance
_cache = SimpleCache(maxsize=1000, default_ttl=3600)

def get_cache():
    """Get global cache instance"""
    return _cache
