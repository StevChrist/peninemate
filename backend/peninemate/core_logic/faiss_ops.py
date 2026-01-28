"""
FAISS Operations - Dynamic index updates
"""
import logging
import json
import faiss
import numpy as np
from pathlib import Path
from peninemate.infrastructure.embedding_client import get_embedding_client
from peninemate.core_logic.qa_db import get_movie_by_tmdb_id

logger = logging.getLogger(__name__)


def add_movie_to_faiss(tmdb_id: int) -> bool:
    """
    Add a new movie to FAISS index dynamically
    
    Args:
        tmdb_id: TMDb movie ID
    
    Returns:
        True if added successfully
    """
    try:
        # Get movie data
        movie = get_movie_by_tmdb_id(tmdb_id)
        if not movie:
            logger.warning(f"⚠️ Movie {tmdb_id} not found in DB")
            return False
        
        # Build text representation
        title = movie.get('title', '')
        overview = movie.get('overview', '')
        genres = movie.get('genres_csv', '')
        directors = ', '.join(movie.get('directors', []))
        cast = ', '.join(movie.get('cast', [])[:5])
        
        text = f"{title}. {overview}. Genres: {genres}. Director: {directors}. Cast: {cast}"
        
        # Generate embedding - ✅ FIXED: Use get_embedding() not encode()
        embedding_client = get_embedding_client()
        embedding = embedding_client.get_embedding(text)
        
        # Load existing index
        data_dir = Path(__file__).parent / "data"
        index_path = data_dir / "faiss_movies.index"
        metadata_path = data_dir / "faiss_metadata.json"
        
        if not index_path.exists():
            logger.warning("⚠️ FAISS index not found")
            return False
        
        # Load index and metadata
        index = faiss.read_index(str(index_path))
        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        # Check if movie already in index
        if any(m['tmdb_id'] == tmdb_id for m in metadata):
            logger.info(f"ℹ️ Movie {tmdb_id} already in FAISS index")
            return True
        
        # Add to index
        embedding_np = np.array([embedding], dtype='float32')
        index.add(embedding_np)
        
        # Add to metadata
        metadata.append({
            'tmdb_id': tmdb_id,
            'title': title,
            'year': movie.get('year')
        })
        
        # Save updated index and metadata
        faiss.write_index(index, str(index_path))
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"✅ Movie {title} added to FAISS index (total: {index.ntotal})")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error adding movie to FAISS: {e}", exc_info=True)
        return False
