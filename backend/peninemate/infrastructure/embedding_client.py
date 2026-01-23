# peninemate/embedding_client.py (FIXED)
from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Union

class EmbeddingClient:
    """Sentence embedding model wrapper."""
    
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """
        Initialize embedding model.
        
        Args:
            model_name: HuggingFace model name
                - all-MiniLM-L6-v2: 384-dim, fast, good quality
                - all-mpnet-base-v2: 768-dim, slower, better quality
        """
        print(f"📦 Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)
        self.dimension = self.model.get_sentence_embedding_dimension()
        print(f"   ✅ Model loaded! Dimension: {self.dimension}")
    
    def embed(self, texts: Union[str, List[str]]) -> np.ndarray:
        """
        Generate embeddings for text(s).
        
        Args:
            texts: Single text or list of texts
        
        Returns:
            numpy array of shape (n, dimension)
        """
        if isinstance(texts, str):
            texts = [texts]
        
        embeddings = self.model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        return embeddings
    
    def embed_single(self, text: str) -> np.ndarray:
        """Generate embedding for single text (convenience method)."""
        return self.embed(text)[0]

# Singleton instance
_embedding_client = None

def get_embedding_client() -> EmbeddingClient:
    """Get singleton embedding client."""
    global _embedding_client
    if _embedding_client is None:
        _embedding_client = EmbeddingClient()
    return _embedding_client

if __name__ == "__main__":
    # Test embedding (NO IMPORT - function already defined above!)
    client = get_embedding_client()  # ← Direct call, no import!
    
    texts = [
        "A thief who steals corporate secrets through dream-sharing technology",
        "Inception is a mind-bending sci-fi thriller",
        "An action movie about bank robbery"
    ]
    
    embeddings = client.embed(texts)
    print(f"\n✅ Test embeddings:")
    print(f"   Shape: {embeddings.shape}")
    print(f"   Sample: {embeddings[0][:5]}...")
    
    # Similarity test
    from sklearn.metrics.pairwise import cosine_similarity
    sim = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
    print(f"   Similarity (text 1 vs 2): {sim:.4f}")
    sim2 = cosine_similarity([embeddings[0]], [embeddings[2]])[0][0]
    print(f"   Similarity (text 1 vs 3): {sim2:.4f}")
