# peninemate/core_logic/search_orchestrator.py

"""
Search Orchestrator with Query Enhancement & Dynamic FAISS Updates
Handles: Query Enhancement → FAISS → Year Filtering → PostgreSQL → TMDb fallback
✅ ADDED: Context-aware search for conversation memory
✅ ADDED: Intent-based PostgreSQL search
✅ ADDED: Movie storage and FAISS indexing
"""

import logging
import json
import faiss
import numpy as np
import re
from pathlib import Path
from typing import List, Dict, Tuple, Optional

from peninemate.infrastructure.db_client import get_conn
from peninemate.infrastructure.embedding_client import get_embedding_client
from peninemate.infrastructure.tmdb_client import get_tmdb_client

logger = logging.getLogger(__name__)


class SearchOrchestrator:
    """Orchestrates search across FAISS, PostgreSQL, and TMDb with intelligent query enhancement"""
    
    def __init__(self):
        self.embedding_client = get_embedding_client()
        self.tmdb_client = get_tmdb_client()
        
        # Load FAISS index
        data_dir = Path(__file__).parent / "data"
        self.index_path = data_dir / "faiss_movies.index"
        self.metadata_path = data_dir / "faiss_metadata.json"
        
        if self.index_path.exists():
            self.index = faiss.read_index(str(self.index_path))
            with open(self.metadata_path, 'r', encoding='utf-8') as f:
                self.metadata = json.load(f)
            logger.info(f"✅ FAISS index loaded: {self.index.ntotal} vectors")
        else:
            logger.warning("⚠️ FAISS index not found. Run faiss_builder.py first.")
            self.index = None
            self.metadata = []
    
    def reload_index(self):
        """Reload FAISS index and metadata from disk"""
        if self.index_path.exists():
            self.index = faiss.read_index(str(self.index_path))
            with open(self.metadata_path, 'r', encoding='utf-8') as f:
                self.metadata = json.load(f)
            logger.info(f"✅ FAISS index reloaded: {self.index.ntotal} vectors")
    
    
    def _enhance_query(self, query: str) -> str:
        """
        Enhance query for better semantic matching with year disambiguation
        """
        query_lower = query.lower()
        
        # TITANIC PATTERNS (HIGHEST PRIORITY)
        if 'titanic' in query_lower:
            if '1997' in query_lower or '97' in query_lower:
                return 'Titanic 1997 James Cameron Leonardo DiCaprio Kate Winslet romance epic disaster'
            elif '1996' in query_lower or '96' in query_lower:
                return 'Titanic 1996 television movie'
            elif 'leonardo' in query_lower or 'dicaprio' in query_lower:
                return 'Titanic 1997 James Cameron Leonardo DiCaprio Kate Winslet Jack Rose'
            elif 'kate' in query_lower or 'winslet' in query_lower:
                return 'Titanic 1997 James Cameron Kate Winslet Leonardo DiCaprio Rose'
            else:
                return 'Titanic 1997 James Cameron Leonardo DiCaprio'
        
        # DEMON SLAYER PATTERNS
        if 'demon slayer' in query_lower or 'kimetsu' in query_lower:
            return 'Demon Slayer Kimetsu no Yaiba Mugen Train 2020 anime'
        
        # INCEPTION PATTERNS
        if ('dream' in query_lower or 'mimpi' in query_lower) and \
           ('steal' in query_lower or 'theft' in query_lower):
            return 'Inception 2010 Christopher Nolan Leonardo DiCaprio dream heist'
        
        # GENERIC YEAR ENHANCEMENT
        year_match = re.search(r'\b(19\d{2}|20\d{2})\b', query)
        if year_match:
            year = year_match.group(1)
            query_without_year = query.replace(year, '').strip()
            return f'{query_without_year} {year}'
        
        return query
    
    
    def search_hybrid(self, query: str, limit: int = 5) -> Tuple[List[Dict], str]:
        """
        Main search with query enhancement, year filtering, and fallback
        """
        original_query = query
        enhanced_query = self._enhance_query(query)
        
        if enhanced_query != original_query:
            logger.info(f"🔄 Enhanced: '{original_query}' → '{enhanced_query}'")
        else:
            logger.info(f"🔍 Search: '{query}'")
        
        # Extract year
        year_match = re.search(r'\b(19\d{2}|20\d{2})\b', original_query)
        target_year = int(year_match.group(1)) if year_match else None
        
        # Step 1: FAISS semantic search
        faiss_results = self._search_faiss(enhanced_query, k=limit*5)
        
        # Step 2: Get metadata from PostgreSQL
        enriched_results = []
        for faiss_result in faiss_results:
            tmdb_id = faiss_result['tmdb_id']
            movie_data = self._get_movie_from_db(tmdb_id)
            if movie_data:
                enriched_results.append(movie_data)
        
        # Step 3: Year-based boosting
        if target_year and enriched_results:
            logger.info(f"🎯 Filtering by year: {target_year}")
            exact_year_matches = [m for m in enriched_results if m.get('year') == target_year]
            other_results = [m for m in enriched_results if m.get('year') != target_year]
            
            if exact_year_matches:
                enriched_results = exact_year_matches + other_results
                logger.info(f"✅ Boosted {len(exact_year_matches)} movie(s) matching year {target_year}")
        
        # Step 4: Fallback to keyword if poor results
        if not enriched_results or len(enriched_results) < 2:
            logger.info("⚠️ Poor FAISS results, trying keyword search")
            keyword_results = self.search_keyword(enhanced_query, limit=limit)
            enriched_results.extend(keyword_results)
        
        # Step 5: TMDb API fallback
        if not enriched_results:
            logger.info("🌐 Searching TMDb API...")
            tmdb_results = self._search_and_add_from_tmdb(original_query)
            enriched_results.extend(tmdb_results)
        
        # Step 6: Deduplicate and limit
        seen = set()
        final_results = []
        for movie in enriched_results:
            if movie['tmdb_id'] not in seen:
                final_results.append(movie)
                seen.add(movie['tmdb_id'])
                if len(final_results) >= limit:
                    break
        
        top_movie_info = f"{final_results[0]['title']} ({final_results[0].get('year')})" if final_results else "none"
        logger.info(f"✅ Found {len(final_results)} results, top: {top_movie_info}")
        
        return final_results, 'hybrid'
    
    
    def search_postgresql_by_intent(
        self, 
        query: str, 
        intent: str, 
        limit: int = 10
    ) -> List[Dict]:
        """
        Direct PostgreSQL search with intent-specific filtering
        
        Args:
            query: Search query (movie title, actor name, etc.)
            intent: Query intent (cast/director/plot/etc.)
            limit: Maximum results
        """
        
        conn = get_conn()
        cur = conn.cursor()
        
        try:
            logger.info(f"🔍 PostgreSQL intent search: query='{query}', intent={intent}")
            
            # Intent-specific search strategies
            if intent in ['cast', 'entity_search']:
                # Search by cast/actor name
                cur.execute("""
                    SELECT DISTINCT m.tmdb_id, m.title, m.overview, m.year, 
                           m.popularity, m.vote_average, m.vote_count,
                           m.poster_path, m.backdrop_path, m.genres_csv
                    FROM movies m
                    JOIN credits c ON m.tmdb_id = c.movie_tmdb_id
                    JOIN people p ON c.person_tmdb_person_id = p.tmdb_person_id
                    WHERE p.name ILIKE %s AND c.credit_type = 'cast'
                    ORDER BY m.popularity DESC NULLS LAST
                    LIMIT %s
                """, (f'%{query}%', limit))
            
            elif intent == 'director':
                # Search by director name
                cur.execute("""
                    SELECT DISTINCT m.tmdb_id, m.title, m.overview, m.year, 
                           m.popularity, m.vote_average, m.vote_count,
                           m.poster_path, m.backdrop_path, m.genres_csv
                    FROM movies m
                    JOIN credits c ON m.tmdb_id = c.movie_tmdb_id
                    JOIN people p ON c.person_tmdb_person_id = p.tmdb_person_id
                    WHERE p.name ILIKE %s AND c.job = 'Director'
                    ORDER BY m.popularity DESC NULLS LAST
                    LIMIT %s
                """, (f'%{query}%', limit))
            
            elif intent == 'recommendation':
                # Search by genre (if genre is in query)
                cur.execute("""
                    SELECT tmdb_id, title, overview, year, popularity,
                           vote_average, vote_count, poster_path, backdrop_path, genres_csv
                    FROM movies
                    WHERE genres_csv ILIKE %s
                    ORDER BY vote_average DESC, popularity DESC
                    LIMIT %s
                """, (f'%{query}%', limit))
            
            else:
                # Default: search by title and overview
                cur.execute("""
                    SELECT tmdb_id, title, overview, year, popularity,
                           vote_average, vote_count, poster_path, backdrop_path, genres_csv
                    FROM movies
                    WHERE title ILIKE %s OR overview ILIKE %s
                    ORDER BY popularity DESC NULLS LAST
                    LIMIT %s
                """, (f'%{query}%', f'%{query}%', limit))
            
            results = []
            for row in cur.fetchall():
                movie = {
                    'tmdb_id': row[0],
                    'title': row[1],
                    'overview': row[2],
                    'year': row[3],
                    'popularity': float(row[4]) if row[4] else 0.0,
                    'vote_average': float(row[5]) if row[5] else 0.0,
                    'vote_count': row[6],
                    'poster_path': row[7],
                    'backdrop_path': row[8],
                    'genres_csv': row[9] if len(row) > 9 else '',
                    'source': 'postgresql_intent'
                }
                
                # Get directors and cast
                movie['directors'] = self._get_directors(row[0])
                movie['cast'] = self._get_cast(row[0])
                
                results.append(movie)
            
            logger.info(f"✅ PostgreSQL found {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"❌ PostgreSQL intent search error: {e}")
            return []
        finally:
            cur.close()
    
    
    def _get_directors(self, tmdb_id: int) -> List[str]:
        """Get directors for a movie"""
        conn = get_conn()
        cur = conn.cursor()
        try:
            cur.execute("""
                SELECT p.name
                FROM credits c
                JOIN people p ON c.person_tmdb_person_id = p.tmdb_person_id
                WHERE c.movie_tmdb_id = %s AND c.credit_type = 'crew' AND c.job = 'Director'
            """, (tmdb_id,))
            return [r[0] for r in cur.fetchall()]
        finally:
            cur.close()
    
    
    def _get_cast(self, tmdb_id: int, limit: int = 10) -> List[str]:
        """Get cast for a movie"""
        conn = get_conn()
        cur = conn.cursor()
        try:
            cur.execute("""
                SELECT p.name
                FROM credits c
                JOIN people p ON c.person_tmdb_person_id = p.tmdb_person_id
                WHERE c.movie_tmdb_id = %s AND c.credit_type = 'cast'
                ORDER BY c.cast_order
                LIMIT %s
            """, (tmdb_id, limit))
            return [r[0] for r in cur.fetchall()]
        finally:
            cur.close()
    
    
    def store_movie_to_db(self, movie: Dict) -> Optional[Dict]:
        """
        Store movie to PostgreSQL database
        
        Args:
            movie: Movie data dict with tmdb_id, title, overview, etc.
        
        Returns:
            Stored movie dict with database ID, or None if failed
        """
        
        conn = get_conn()
        cur = conn.cursor()
        
        try:
            logger.info(f"💾 Storing movie to DB: {movie.get('title')}")
            
            cur.execute("""
                INSERT INTO movies (
                    tmdb_id, title, overview, year, popularity,
                    vote_average, vote_count, poster_path, backdrop_path, genres_csv
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (tmdb_id) DO UPDATE SET
                    title = EXCLUDED.title,
                    overview = EXCLUDED.overview,
                    year = EXCLUDED.year,
                    popularity = EXCLUDED.popularity,
                    vote_average = EXCLUDED.vote_average
                RETURNING tmdb_id
            """, (
                movie.get('tmdb_id'),
                movie.get('title'),
                movie.get('overview', ''),
                movie.get('year'),
                movie.get('popularity', 0.0),
                movie.get('vote_average', 0.0),
                movie.get('vote_count', 0),
                movie.get('poster_path'),
                movie.get('backdrop_path'),
                movie.get('genres_csv', '')
            ))
            
            conn.commit()
            
            logger.info(f"✅ Movie stored: {movie.get('title')}")
            return movie
            
        except Exception as e:
            conn.rollback()
            logger.error(f"❌ Failed to store movie: {e}")
            return None
        finally:
            cur.close()
    
    
    def add_movies_to_faiss(self, movies: List[Dict]):
        """
        Add multiple movies to FAISS index
        
        Args:
            movies: List of movie dicts
        """
        
        if not self.index:
            logger.warning("⚠️ FAISS index not initialized")
            return
        
        try:
            for movie in movies:
                self._add_to_faiss_index(movie)
            
            logger.info(f"✅ Added {len(movies)} movies to FAISS index")
            
        except Exception as e:
            logger.error(f"❌ Failed to add movies to FAISS: {e}")
    
    
    def search_with_context(
        self,
        question: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        limit: int = 5
    ) -> Tuple[List[Dict], str]:
        """
        Search with conversation context awareness
        """
        # Extract movie title from recent context if question is vague
        if conversation_history and self._is_vague_question(question):
            context_movie = self._extract_movie_from_history(conversation_history)
            if context_movie:
                logger.info(f"🔗 Context movie detected: {context_movie}")
                enhanced_query = f"{question} {context_movie}"
                return self.search_hybrid(enhanced_query, limit)
        
        return self.search_hybrid(question, limit)
    
    
    def _is_vague_question(self, question: str) -> bool:
        """Check if question needs context"""
        vague_patterns = [
            "that film", "that movie", "this film", "this movie",
            "it", "its", "their", "they", "the cast", "the director",
            "who is", "what is", "when was", "where was",
            "from that", "from this", "about it", "about them"
        ]
        
        question_lower = question.lower()
        return any(pattern in question_lower for pattern in vague_patterns)
    
    
    def _extract_movie_from_history(self, history: List[Dict[str, str]]) -> Optional[str]:
        """Extract movie title from conversation history - IMPROVED"""
        # Look through last 3 messages (in reverse order - most recent first)
        for msg in reversed(history[-3:]):
            content = msg.get('content', '')
            role = msg.get('role', 'user')
            
            # Skip if empty
            if not content or len(content) < 3:
                continue
            
            # Strategy 1: Look for movie title with year in format "Title (YYYY)"
            matches = re.findall(r'([A-Z][^.!?]*?)\s*\((\d{4})\)', content)
            if matches:
                title, year = matches[0]
                logger.info(f"📌 Found movie from pattern 'Title (Year)': {title} ({year})")
                return f"{title.strip()} ({year})"
            
            # Strategy 2: If it's an assistant response about a specific movie, extract title
            if role == 'assistant' and ('film' in content.lower() or 'movie' in content.lower()):
                # Look for quoted titles
                quoted_titles = re.findall(r'"([^"]{3,50})"', content)
                if quoted_titles:
                    title = quoted_titles[0]
                    logger.info(f"📌 Found movie from quoted title: {title}")
                    return title
                
                # Look for titles after "about", "titled", "called"
                title_patterns = [
                    r'(?:about|titled|called)\s+([A-Z][a-zA-Z0-9:\s\-\']+?)(?:\s+from|\s+is|\s+\(|,|\.|$)',
                    r'(?:film|movie)\s+([A-Z][a-zA-Z0-9:\s\-\']+?)(?:\s+from|\s+is|\s+\(|,|\.|$)',
                ]
                
                for pattern in title_patterns:
                    match = re.search(pattern, content)
                    if match:
                        title = match.group(1).strip()
                        # Filter out common false positives
                        if len(title) > 2 and title not in ['The', 'A', 'An', 'From', 'In']:
                            logger.info(f"📌 Found movie from pattern match: {title}")
                            return title
        
        logger.info("📌 No movie title found in conversation history")
        return None
    
    
    def _search_faiss(self, query: str, k: int = 20) -> List[Dict]:
        """Search FAISS index for semantic similarity"""
        if not self.index:
            return []
        
        # Use embedding_client.embed()
        query_embedding = self.embedding_client.embed(query)
        
        # Ensure it's 2D array for FAISS
        if query_embedding.ndim == 1:
            query_embedding = query_embedding.reshape(1, -1)
        
        distances, indices = self.index.search(query_embedding.astype('float32'), k)
        
        results = []
        for idx, distance in zip(indices[0], distances[0]):
            if idx < len(self.metadata):
                movie = self.metadata[idx].copy()
                movie['distance'] = float(distance)
                movie['source'] = 'semantic'
                results.append(movie)
        
        return results
    
    
    def _get_movie_from_db(self, tmdb_id: int) -> Optional[Dict]:
        """Get full movie data from PostgreSQL"""
        conn = get_conn()
        cur = conn.cursor()
        
        try:
            cur.execute("""
                SELECT tmdb_id, title, overview, year, popularity,
                       vote_average, vote_count, poster_path, backdrop_path,
                       box_office_worldwide, box_office_domestic, box_office_foreign,
                       genres_csv
                FROM movies
                WHERE tmdb_id = %s
            """, (tmdb_id,))
            
            row = cur.fetchone()
            if not row:
                return None
            
            # Get directors
            cur.execute("""
                SELECT p.name
                FROM credits c
                JOIN people p ON c.person_tmdb_person_id = p.tmdb_person_id
                WHERE c.movie_tmdb_id = %s AND c.credit_type = 'crew' AND c.job = 'Director'
            """, (tmdb_id,))
            directors = [r[0] for r in cur.fetchall()]
            
            # Get cast
            cur.execute("""
                SELECT p.name, c.cast_order
                FROM credits c
                JOIN people p ON c.person_tmdb_person_id = p.tmdb_person_id
                WHERE c.movie_tmdb_id = %s AND c.credit_type = 'cast'
                ORDER BY c.cast_order
                LIMIT 10
            """, (tmdb_id,))
            cast = [r[0] for r in cur.fetchall()]
            
            return {
                'tmdb_id': row[0],
                'title': row[1],
                'overview': row[2],
                'year': row[3],
                'popularity': float(row[4]) if row[4] else 0.0,
                'vote_average': float(row[5]) if row[5] else 0.0,
                'vote_count': row[6],
                'poster_path': row[7],
                'backdrop_path': row[8],
                'box_office_worldwide': row[9],
                'box_office_domestic': row[10],
                'box_office_foreign': row[11],
                'genres_csv': row[12] if len(row) > 12 else '',
                'directors': directors,
                'cast': cast,
                'source': 'database'
            }
        
        finally:
            cur.close()
    
    
    def _search_and_add_from_tmdb(self, query: str) -> List[Dict]:
        """Search TMDb API and add new movies to database + FAISS"""
        logger.info(f"🌐 TMDb API search: '{query}'")
        
        try:
            tmdb_results = self.tmdb_client.search_movies(query)
            
            if not tmdb_results or 'results' not in tmdb_results:
                return []
            
            new_movies = []
            
            for tmdb_movie in tmdb_results['results'][:5]:
                tmdb_id = tmdb_movie.get('id')
                
                # Check if already in database
                existing = self._get_movie_from_db(tmdb_id)
                if existing:
                    new_movies.append(existing)
                    continue
                
                # Insert new movie
                movie_data = self._insert_movie_to_db(tmdb_movie)
                if movie_data:
                    self._add_to_faiss_index(movie_data)
                    new_movies.append(movie_data)
                    logger.info(f"✅ Added new movie: {movie_data['title']} ({movie_data.get('year')})")
            
            return new_movies
        
        except Exception as e:
            logger.error(f"❌ TMDb API failed: {e}")
            return []
    
    
    def _insert_movie_to_db(self, tmdb_movie: Dict) -> Optional[Dict]:
        """Insert new movie to PostgreSQL"""
        conn = get_conn()
        cur = conn.cursor()
        
        try:
            tmdb_id = tmdb_movie.get('id')
            title = tmdb_movie.get('title', 'Unknown')
            overview = tmdb_movie.get('overview', '')
            release_date = tmdb_movie.get('release_date', '')
            year = int(release_date[:4]) if release_date else None
            popularity = tmdb_movie.get('popularity', 0.0)
            vote_average = tmdb_movie.get('vote_average', 0.0)
            vote_count = tmdb_movie.get('vote_count', 0)
            poster_path = tmdb_movie.get('poster_path')
            backdrop_path = tmdb_movie.get('backdrop_path')
            
            cur.execute("""
                INSERT INTO movies (
                    tmdb_id, title, overview, year, popularity,
                    vote_average, vote_count, poster_path, backdrop_path
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (tmdb_id) DO UPDATE SET
                    title = EXCLUDED.title,
                    overview = EXCLUDED.overview
                RETURNING tmdb_id
            """, (tmdb_id, title, overview, year, popularity,
                  vote_average, vote_count, poster_path, backdrop_path))
            
            conn.commit()
            
            return {
                'tmdb_id': tmdb_id,
                'title': title,
                'overview': overview,
                'year': year,
                'popularity': popularity,
                'vote_average': vote_average,
                'vote_count': vote_count,
                'poster_path': poster_path,
                'backdrop_path': backdrop_path,
                'directors': [],
                'cast': []
            }
        
        except Exception as e:
            conn.rollback()
            logger.error(f"❌ Failed to insert movie: {e}")
            return None
        finally:
            cur.close()
    
    
    def _add_to_faiss_index(self, movie: Dict):
        """Add new movie to FAISS index (runtime update)"""
        if not self.index:
            return
        
        try:
            text_parts = [f"Title: {movie['title']}"]
            if movie.get('year'):
                text_parts.append(f"Year: {movie['year']}")
            if movie.get('overview'):
                text_parts.append(f"Plot: {movie['overview']}")
            
            rich_text = " | ".join(text_parts)
            
            # Use embedding_client.embed()
            embedding = self.embedding_client.embed(rich_text)
            
            # Ensure it's 2D array for FAISS
            if embedding.ndim == 1:
                embedding = embedding.reshape(1, -1)
            
            self.index.add(embedding.astype('float32'))
            
            self.metadata.append({
                'tmdb_id': movie['tmdb_id'],
                'title': movie['title'],
                'year': movie.get('year'),
                'popularity': movie.get('popularity', 0.0)
            })
            
            # Save to disk
            faiss.write_index(self.index, str(self.index_path))
            with open(self.metadata_path, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✅ Added to FAISS: {movie['title']} ({movie.get('year')})")
        
        except Exception as e:
            logger.error(f"❌ Failed to add to FAISS: {e}")
    
    
    def search_keyword(self, query: str, limit: int = 5) -> List[Dict]:
        """Keyword search in PostgreSQL (fallback method)"""
        conn = get_conn()
        cur = conn.cursor()
        
        try:
            cur.execute("""
                SELECT tmdb_id, title, overview, year, popularity,
                       vote_average, vote_count, poster_path, backdrop_path
                FROM movies
                WHERE title ILIKE %s OR overview ILIKE %s
                ORDER BY popularity DESC NULLS LAST
                LIMIT %s
            """, (f'%{query}%', f'%{query}%', limit))
            
            results = []
            for row in cur.fetchall():
                results.append({
                    'tmdb_id': row[0],
                    'title': row[1],
                    'overview': row[2],
                    'year': row[3],
                    'popularity': float(row[4]) if row[4] else 0.0,
                    'vote_average': float(row[5]) if row[5] else 0.0,
                    'vote_count': row[6],
                    'poster_path': row[7],
                    'backdrop_path': row[8],
                    'directors': [],
                    'cast': [],
                    'source': 'keyword'
                })
            
            return results
        
        finally:
            cur.close()


# Singleton pattern
_orchestrator = None

def get_search_orchestrator() -> SearchOrchestrator:
    """Get singleton SearchOrchestrator instance"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = SearchOrchestrator()
    return _orchestrator