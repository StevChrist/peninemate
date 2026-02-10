"""
FAISS Operations
Dynamic index update using OpenAI embeddings
"""

import logging
import json
from pathlib import Path

import faiss
import numpy as np

from peninemate.infrastructure.embedding_client import get_embedding_client
from peninemate.core_logic.qa_db import get_movie_by_tmdb_id

logger = logging.getLogger(__name__)


# ============================================================================
# Helpers
# ============================================================================

def _build_movie_text(movie: dict) -> str:
    """
    Build text representation for a single movie.
    Must stay CONSISTENT with faiss_builder.py
    """
    parts = []

    title = movie.get("title")
    if title:
        parts.append(f"Title: {title}")

    year = movie.get("year")
    if year:
        parts.append(f"Year: {year}")

    overview = movie.get("overview")
    if overview:
        parts.append(f"Plot: {overview}")

    genres = movie.get("genres_csv")
    if genres:
        parts.append(f"Genres: {genres}")

    directors = movie.get("directors", [])
    if directors:
        parts.append(f"Director: {', '.join(directors[:3])}")

    cast = movie.get("cast", [])
    if cast:
        parts.append(f"Cast: {', '.join(cast[:5])}")

    return " | ".join(parts)


# ============================================================================
# Public API
# ============================================================================

def add_movie_to_faiss(tmdb_id: int) -> bool:
    """
    Add a new movie to FAISS index dynamically.

    Args:
        tmdb_id: TMDb movie ID

    Returns:
        True if added or already exists, False otherwise
    """
    try:
        # ------------------------------------------------------------------
        # Fetch movie
        # ------------------------------------------------------------------
        movie = get_movie_by_tmdb_id(tmdb_id)
        if not movie:
            logger.warning(f"⚠️ Movie {tmdb_id} not found in DB")
            return False

        # ------------------------------------------------------------------
        # Load FAISS index + metadata
        # ------------------------------------------------------------------
        data_dir = Path(__file__).parent / "data"
        index_path = data_dir / "faiss_movies.index"
        metadata_path = data_dir / "faiss_metadata.json"

        if not index_path.exists() or not metadata_path.exists():
            logger.error("❌ FAISS index or metadata not found")
            return False

        index = faiss.read_index(str(index_path))

        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        # Prevent duplicate insert
        if any(m["tmdb_id"] == tmdb_id for m in metadata):
            logger.info(f"ℹ️ Movie {tmdb_id} already exists in FAISS index")
            return True

        # ------------------------------------------------------------------
        # Build text + embedding
        # ------------------------------------------------------------------
        text = _build_movie_text(movie)

        if not text or len(text.split()) < 3:
            logger.warning(f"⚠️ Movie {tmdb_id} text too weak, skipping")
            return False

        embedding_client = get_embedding_client()
        vector = embedding_client.embed_single(text)

        # Ensure correct shape
        vector_np = np.asarray(vector, dtype="float32").reshape(1, -1)

        # ------------------------------------------------------------------
        # Add to FAISS
        # ------------------------------------------------------------------
        index.add(vector_np)

        metadata.append(
            {
                "tmdb_id": tmdb_id,
                "title": movie.get("title"),
                "year": movie.get("year"),
                "popularity": float(movie.get("popularity", 0.0)),
            }
        )

        # ------------------------------------------------------------------
        # Persist
        # ------------------------------------------------------------------
        faiss.write_index(index, str(index_path))
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        logger.info(
            f"✅ Movie '{movie.get('title')}' added to FAISS "
            f"(total vectors: {index.ntotal})"
        )

        return True

    except Exception as e:
        logger.error(f"❌ Error adding movie {tmdb_id} to FAISS", exc_info=True)
        return False