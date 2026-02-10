import sys
from pathlib import Path
import json

import faiss
import numpy as np
from tqdm import tqdm

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from peninemate.infrastructure.db_client import get_conn
from peninemate.infrastructure.embedding_client import get_embedding_client


# ============================================================================
# Metadata builder
# ============================================================================

def build_rich_metadata_text(movie_row, conn) -> str:
    """
    Build rich text combining ALL metadata.
    Used as FAISS document text.
    """
    tmdb_id, title, overview, year, popularity = movie_row
    text_parts = []

    # 1. Title (highest weight)
    if title:
        text_parts.append(f"Title: {title}")

    # 2. Year
    if year:
        text_parts.append(f"Year: {year}")

    # 3. Overview / plot
    if overview:
        text_parts.append(f"Plot: {overview}")

    cursor = conn.cursor()

    # 4. Directors
    try:
        cursor.execute(
            """
            SELECT DISTINCT p.name
            FROM credits c
            JOIN people p ON c.person_tmdb_person_id = p.tmdb_person_id
            WHERE c.movie_tmdb_id = %s
              AND c.credit_type = 'crew'
              AND c.job = 'Director'
            LIMIT 3
            """,
            (tmdb_id,),
        )
        directors = [row[0] for row in cursor.fetchall()]
        if directors:
            text_parts.append(f"Director: {', '.join(directors)}")
    except Exception:
        pass

    # 5. Top cast
    try:
        cursor.execute(
            """
            SELECT p.name
            FROM credits c
            JOIN people p ON c.person_tmdb_person_id = p.tmdb_person_id
            WHERE c.movie_tmdb_id = %s
              AND c.credit_type = 'cast'
            ORDER BY c.cast_order ASC
            LIMIT 8
            """,
            (tmdb_id,),
        )
        cast = [row[0] for row in cursor.fetchall()]
        if cast:
            text_parts.append(f"Cast: {', '.join(cast)}")
    except Exception:
        pass

    cursor.close()
    return " | ".join(text_parts)


# ============================================================================
# FAISS Builder
# ============================================================================

def build_faiss_index():
    """
    Build FAISS index using OpenAI embeddings (text-embedding-3-small).
    Supports semantic search over title, plot, director, and cast.
    """
    print("=" * 72)
    print("🔨 BUILDING FAISS INDEX (OpenAI Embeddings)")
    print("=" * 72)

    # Load embedding client
    embedding_client = get_embedding_client()
    dimension = embedding_client.dimension

    # Fetch movies
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT tmdb_id, title, overview, year, popularity
        FROM movies
        ORDER BY tmdb_id
        """
    )
    movies = cursor.fetchall()
    print(f"📊 Found {len(movies)} movies")

    documents = []
    metadata = []
    skipped = 0

    print("\n🔧 Building rich metadata text...")
    for movie in tqdm(movies, desc="Processing movies"):
        tmdb_id, title, overview, year, popularity = movie

        rich_text = build_rich_metadata_text(movie, conn)

        # Skip weak documents
        if not rich_text or len(rich_text.split()) < 3:
            skipped += 1
            continue

        documents.append(rich_text)
        metadata.append(
            {
                "tmdb_id": tmdb_id,
                "title": title,
                "year": year,
                "popularity": float(popularity) if popularity else 0.0,
            }
        )

    print(f"\n✅ Documents ready: {len(documents)} (skipped {skipped})")

    # ------------------------------------------------------------------
    # Generate embeddings (OpenAI)
    # ------------------------------------------------------------------

    print("\n🧮 Generating embeddings with OpenAI...")
    embeddings = embedding_client.embed(documents)

    print(
        f"✅ Embeddings generated: {embeddings.shape[0]} vectors "
        f"(dim={embeddings.shape[1]})"
    )

    # ------------------------------------------------------------------
    # Build FAISS index (Cosine similarity via Inner Product)
    # ------------------------------------------------------------------

    print("\n🏗️ Building FAISS index (IndexFlatIP)...")
    index = faiss.IndexFlatIP(dimension)
    index.add(embeddings)

    print(f"✅ FAISS index ready with {index.ntotal} vectors")

    # ------------------------------------------------------------------
    # Save index + metadata
    # ------------------------------------------------------------------

    data_dir = Path(__file__).parent / "data"
    data_dir.mkdir(exist_ok=True)

    index_path = data_dir / "faiss_movies.index"
    metadata_path = data_dir / "faiss_metadata.json"

    faiss.write_index(index, str(index_path))
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    print(f"💾 Index saved    : {index_path}")
    print(f"💾 Metadata saved : {metadata_path}")

    cursor.close()
    conn.close()

    print("\n" + "=" * 72)
    print("✅ FAISS BUILD COMPLETE (OpenAI)")
    print("=" * 72)
    print(f"📈 Total vectors : {index.ntotal}")
    print(f"📏 Dimension     : {dimension}")
    print("🎯 Similarity    : Cosine (via Inner Product)")
    print("🚀 Ready for GPT-5 nano RAG pipeline")
    print("=" * 72)

    return index, metadata


if __name__ == "__main__":
    build_faiss_index()
