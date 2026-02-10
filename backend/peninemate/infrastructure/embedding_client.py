"""
OpenAI Embedding Client
Uses text-embedding-3-small for semantic search (FAISS)
"""

import os
import logging
from typing import List, Union, Optional

import numpy as np
from openai import OpenAI

logger = logging.getLogger(__name__)


class EmbeddingClient:
    """
    OpenAI embedding wrapper.
    Designed for FAISS semantic search.
    """

    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")

        self.client = OpenAI(api_key=api_key)

        self.model = os.getenv(
            "OPENAI_EMBEDDING_MODEL",
            "text-embedding-3-small"
        )

        # Official dimension for text-embedding-3-small
        self.dimension = 1536

        # Safe batch size (OpenAI friendly)
        self.batch_size = 32

        logger.info(
            f"✅ OpenAI embedding initialized "
            f"(model={self.model}, dim={self.dimension})"
        )

    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------

    def embed(self, texts: Union[str, List[str]]) -> np.ndarray:
        """
        Generate normalized embeddings for one or more texts.

        Args:
            texts: Single string or list of strings

        Returns:
            np.ndarray of shape (n, dim) with float32 dtype
        """

        if isinstance(texts, str):
            texts = [texts]

        if not texts:
            raise ValueError("Texts must not be empty")

        all_embeddings: List[np.ndarray] = []

        try:
            for batch in self._batch_iter(texts, self.batch_size):
                response = self.client.embeddings.create(
                    model=self.model,
                    input=batch,
                )

                batch_embeddings = [
                    np.array(item.embedding, dtype=np.float32)
                    for item in response.data
                ]

                all_embeddings.extend(batch_embeddings)

            embeddings = np.vstack(all_embeddings)

            # Normalize for cosine similarity / FAISS
            embeddings = self._l2_normalize(embeddings)

            return embeddings

        except Exception as e:
            logger.error(
                f"❌ Failed to generate embeddings: {e}",
                exc_info=True
            )
            raise RuntimeError("Embedding generation failed")

    def embed_single(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text.

        Returns:
            np.ndarray of shape (dim,)
        """
        return self.embed([text])[0]

    # ---------------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------------

    @staticmethod
    def _batch_iter(items: List[str], batch_size: int):
        """Yield batches of items."""
        for i in range(0, len(items), batch_size):
            yield items[i:i + batch_size]

    @staticmethod
    def _l2_normalize(vectors: np.ndarray) -> np.ndarray:
        """L2 normalize vectors row-wise."""
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        return vectors / np.clip(norms, 1e-12, None)


# ============================================================================
# Singleton accessor
# ============================================================================

_embedding_client: Optional[EmbeddingClient] = None


def get_embedding_client() -> EmbeddingClient:
    """Get singleton embedding client."""
    global _embedding_client
    if _embedding_client is None:
        _embedding_client = EmbeddingClient()
    return _embedding_client


# ============================================================================
# Manual test
# ============================================================================

if __name__ == "__main__":
    client = get_embedding_client()

    texts = [
        "A thief who steals corporate secrets through dream-sharing technology",
        "Inception is a mind-bending sci-fi thriller",
        "An action movie about bank robbery",
    ]

    embeddings = client.embed(texts)

    print("\n✅ Embedding test")
    print(f"Shape      : {embeddings.shape}")
    print(f"Dimension  : {embeddings.shape[1]}")
    print(f"First vec  : {embeddings[0][:5]}")

    # Cosine similarity sanity check
    from sklearn.metrics.pairwise import cosine_similarity

    sim_1_2 = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
    sim_1_3 = cosine_similarity([embeddings[0]], [embeddings[2]])[0][0]

    print(f"Similarity (1 vs 2): {sim_1_2:.4f}")
    print(f"Similarity (1 vs 3): {sim_1_3:.4f}")
