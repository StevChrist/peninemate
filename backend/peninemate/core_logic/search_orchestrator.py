# peninemate/core_logic/search_orchestrator.py

"""
Hybrid Search Orchestrator: PostgreSQL + FAISS + TMDb
With improved semantic search (query expansion, score filtering, reranking)
Priority: Keyword → Semantic → API Fallback
"""

import faiss
import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional
import sys

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from peninemate.infrastructure.embedding_client import get_embedding_client
from peninemate.infrastructure.db_client import get_conn


class SearchOrchestrator:
    """
    Hybrid search coordinator with PostgreSQL keyword and FAISS semantic search.
    Includes query expansion, score filtering, and reranking for better relevance.
    """
    
    def __init__(self):
        """Initialize FAISS index and metadata."""
        self.embedding_client = None
        self.faiss_index = None
        self.metadata = None
        # Load FAISS index on initialization
        self._load_faiss_index()
    
    def _load_faiss_index(self):
        """Load FAISS index and metadata from disk."""
        # Get paths relative to this file
        data_dir = Path(__file__).parent / "data"
        index_path = data_dir / "faiss_movies.index"
        metadata_path = data_dir / "faiss_metadata.json"
        
        # Check if files exist
        if not index_path.exists():
            print(f"⚠️  FAISS index not found: {index_path}")
            print(f"   Run: python peninemate/faiss_builder.py --rebuild")
            return False
        
        if not metadata_path.exists():
            print(f"⚠️  FAISS metadata not found: {metadata_path}")
            return False
        
        try:
            # Load FAISS index
            print("📦 Loading embedding model...")
            self.embedding_client = get_embedding_client()
            self.faiss_index = faiss.read_index(str(index_path))
            
            with open(metadata_path, 'r', encoding='utf-8') as f:
                self.metadata = json.load(f)
            
            print(f"✅ FAISS index loaded: {self.faiss_index.ntotal} vectors")
            return True
        
        except Exception as e:
            print(f"❌ Failed to load FAISS index: {e}")
            return False
    
    def _expand_query(self, query: str) -> str:
        """
        Expand query with synonyms and context for better semantic search
        
        Args:
            query: Original search query
        
        Returns:
            Expanded query string
        """
        query_lower = query.lower()
        
        # Common expansions
        expansions = {
            # Directors (last name → full name + context)
            'nolan': 'christopher nolan director filmmaker',
            'tarantino': 'quentin tarantino director filmmaker',
            'spielberg': 'steven spielberg director filmmaker',
            'scorsese': 'martin scorsese director filmmaker',
            'kubrick': 'stanley kubrick director filmmaker',
            'fincher': 'david fincher director filmmaker',
            'villeneuve': 'denis villeneuve director filmmaker',
            
            # Actors (partial name → full name)
            'dicaprio': 'leonardo dicaprio actor',
            'denzel': 'denzel washington actor',
            'morgan freeman': 'morgan freeman actor',
            
            # Genres (expand with related terms)
            'sci-fi': 'science fiction space futuristic technology',
            'scifi': 'science fiction space futuristic technology',
            'action': 'action adventure thriller exciting',
            'horror': 'horror scary terror frightening suspense',
            'comedy': 'comedy funny humor amusing hilarious',
            'drama': 'drama emotional story character',
            'romance': 'romance love relationship romantic',
            
            # Themes
            'space': 'space cosmos universe galaxy planets astronomy',
            'war': 'war military combat battle soldier',
            'love': 'love romance relationship romantic affection',
            'crime': 'crime criminal heist robbery detective',
            'time travel': 'time travel temporal paradox future past',
            
            # Marvel/DC/Franchises
            'marvel': 'marvel cinematic universe mcu superhero avengers',
            'mcu': 'marvel cinematic universe mcu superhero',
            'dc': 'dc comics superhero batman superman wonder woman',
            'star wars': 'star wars jedi sith force galaxy',
        }
        
        # Find matching expansion (check if any keyword is in query)
        for key, expansion in expansions.items():
            if key in query_lower:
                return f"{query} {expansion}"
        
        return query
    
    def _rerank_results(self, results: list) -> list:
        """
        Rerank results by combining semantic similarity + popularity
        
        Args:
            results: List of movies with similarity_score
        
        Returns:
            Reranked list of movies sorted by final_score
        """
        for r in results:
            # Get scores
            similarity_score = r.get('similarity_score', 0.0)
            popularity = r.get('popularity', 0.0)
            
            # Normalize popularity (0-100 → 0-1)
            # Using min() to cap at 1.0 for very popular movies
            norm_popularity = min(popularity / 100.0, 1.0)
            
            # Weighted combination
            # 70% semantic relevance, 30% popularity
            # Adjust weights based on your preference
            r['final_score'] = 0.7 * similarity_score + 0.3 * norm_popularity
        
        # Sort by final score (highest first)
        return sorted(results, key=lambda x: x.get('final_score', 0), reverse=True)
    
    def search_keyword(self, query: str, limit: int = 5) -> List[Dict]:
        """
        Search movies by keyword (title match) in PostgreSQL.
        IMPROVED: Prioritizes exact matches over partial matches.
        
        Args:
            query: Search query
            limit: Max results
        
        Returns:
            List of movie dicts with 'source': 'keyword'
        """
        conn = get_conn()
        cur = conn.cursor()
        
        try:
            # IMPROVED: Exact match gets priority 0, partial match gets priority 1
            # Within same priority, sort by popularity
            cur.execute("""
                SELECT tmdb_id, title, year, overview, popularity,
                       box_office_worldwide, box_office_domestic, box_office_foreign
                FROM movies
                WHERE title ILIKE %s
                ORDER BY 
                    CASE WHEN LOWER(title) = LOWER(%s) THEN 0 ELSE 1 END,
                    popularity DESC NULLS LAST
                LIMIT %s
            """, (f"%{query}%", query, limit))
            
            results = []
            for row in cur.fetchall():
                results.append({
                    'tmdb_id': row[0],
                    'title': row[1],
                    'year': row[2],
                    'overview': row[3],
                    'popularity': row[4],
                    'box_office_worldwide': row[5],
                    'box_office_domestic': row[6],
                    'box_office_foreign': row[7],
                    'source': 'keyword'
                })
            
            return results
        
        finally:
            cur.close()
            conn.close()
    
    def search_semantic(self, query: str, k: int = 20) -> List[Dict]:
        """
        Search using FAISS semantic similarity with improved filtering and reranking.
        
        Args:
            query: Search query
            k: Number of candidates to fetch (will filter to top 5)
        
        Returns:
            List of movie dicts with similarity_score and final_score
        """
        # Check if FAISS is loaded
        if self.faiss_index is None or self.metadata is None:
            print("⚠️  FAISS index not loaded")
            return []
        
        if self.embedding_client is None:
            print("⚠️  Embedding client not loaded")
            return []
        
        try:
            # Expand query for better results
            expanded_query = self._expand_query(query)
            
            # Generate query embedding
            query_embedding = self.embedding_client.model.encode(
                [expanded_query],
                convert_to_numpy=True
            )
            
            # Search FAISS (fetch k candidates, we'll filter later)
            distances, indices = self.faiss_index.search(
                query_embedding.astype('float32'),
                k
            )
            
            # Convert L2 distance to similarity score (0-1)
            # L2 distance: smaller = more similar
            # Similarity = 1 / (1 + distance)
            similarities = 1 / (1 + distances[0])
            
            # Filter by minimum similarity threshold
            MIN_SIMILARITY = 0.4  # Tune this (0-1, higher = stricter)
            
            filtered_results = []
            for idx, sim in zip(indices[0], similarities):
                # Check valid index and minimum similarity
                if idx >= 0 and idx < len(self.metadata) and sim >= MIN_SIMILARITY:
                    movie = self.metadata[idx].copy()
                    movie['similarity_score'] = float(sim)
                    movie['source'] = 'semantic'
                    filtered_results.append(movie)
            
            # Rerank by combining semantic similarity + popularity
            reranked = self._rerank_results(filtered_results)
            
            # Return top 5 after filtering and reranking
            return reranked[:5]
        
        except Exception as e:
            print(f"❌ Semantic search error: {e}")
            return []
    
    def search_hybrid(self, query: str, limit: int = 5) -> List[Dict]:
        """
        Hybrid search: Try keyword first, then add semantic results if needed.
        Now with improved semantic search (query expansion + reranking).
        
        Priority:
        1. Keyword search (exact title match)
        2. Semantic search (FAISS) with filtering and reranking
        
        Args:
            query: Search query
            limit: Max results
        
        Returns:
            List of movies (deduplicated by tmdb_id)
        """
        # Phase 1: Keyword search
        keyword_results = self.search_keyword(query, limit=limit)
        
        # If keyword found enough results, return them
        if len(keyword_results) >= limit:
            return keyword_results[:limit]
        
        # Phase 2: Semantic search to fill remaining slots (now improved!)
        semantic_results = self.search_semantic(query, k=20)  # Fetch 20, filter to 5
        
        # Combine and deduplicate
        seen_ids = {r['tmdb_id'] for r in keyword_results}
        combined = keyword_results.copy()
        
        for r in semantic_results:
            if r['tmdb_id'] not in seen_ids:
                combined.append(r)
                seen_ids.add(r['tmdb_id'])
                
                # Stop when we have enough results
                if len(combined) >= limit:
                    break
        
        return combined[:limit]


# ============================================================
# Singleton Pattern
# ============================================================

_orchestrator = None

def get_search_orchestrator() -> SearchOrchestrator:
    """Get singleton SearchOrchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = SearchOrchestrator()
    return _orchestrator


# ============================================================
# Testing
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("IMPROVED SEARCH ORCHESTRATOR TEST")
    print("=" * 60)
    
    orchestrator = get_search_orchestrator()
    
    # Test 1: Query Expansion
    print("\n" + "=" * 60)
    print("TEST 1: Query Expansion")
    print("=" * 60)
    test_queries = ["nolan films", "space movies", "marvel", "sci-fi action"]
    for query in test_queries:
        expanded = orchestrator._expand_query(query)
        print(f"Original: '{query}'")
        print(f"Expanded: '{expanded}'")
        print()
    
    # Test 2: Exact Match Priority (Franchise Movies)
    print("=" * 60)
    print("TEST 2: Exact Match Priority (Franchise Fix)")
    print("=" * 60)
    
    test_queries = ["The Matrix", "Mission Impossible", "Inception"]
    for query in test_queries:
        print(f"\nQuery: '{query}'")
        results = orchestrator.search_keyword(query, limit=5)
        for i, r in enumerate(results, 1):
            match_type = "EXACT" if r['title'].lower() == query.lower() else "PARTIAL"
            print(f"  {i}. {r['title']} ({r.get('year', 'N/A')}) [{match_type}]")
    
    # Test 3: Semantic Search with Filtering
    print("\n" + "=" * 60)
    print("TEST 3: Semantic Search with Filtering & Reranking")
    print("=" * 60)
    query = "dream heist movie"
    print(f"\nQuery: '{query}'")
    results = orchestrator.search_semantic(query, k=20)
    print(f"Found {len(results)} results after filtering:")
    for i, r in enumerate(results, 1):
        sim_score = r.get('similarity_score', 0)
        final_score = r.get('final_score', 0)
        print(f"  {i}. {r['title']} ({r.get('year', 'N/A')})")
        print(f"     Similarity: {sim_score:.3f} | Final Score: {final_score:.3f}")
    
    # Test 4: Hybrid Search
    print("\n" + "=" * 60)
    print("TEST 4: Hybrid Search")
    print("=" * 60)
    test_queries = ["Inception", "christopher nolan", "space exploration"]
    for query in test_queries:
        print(f"\nQuery: '{query}'")
        results = orchestrator.search_hybrid(query, limit=5)
        for i, r in enumerate(results, 1):
            print(f"  {i}. {r['title']} ({r.get('year', 'N/A')}) [{r['source']}]")
    
    print("\n" + "=" * 60)
    print("✅ All tests complete!")
    print("=" * 60)