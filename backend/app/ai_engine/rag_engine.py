"""
MedAssist AI - RAG (Retrieval Augmented Generation) System
FAISS vector store for knowledge base search and context retrieval
"""

import os
import json
import logging
import numpy as np
from typing import Optional, List, Dict
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Lazy-load heavy ML libraries
_embedder = None
_faiss_index = None


@dataclass
class KnowledgeChunk:
    """A chunk of knowledge base content with metadata"""
    id: str
    title: str
    content: str
    category: str
    embedding: Optional[np.ndarray] = None


class VectorStore:
    """
    FAISS-backed vector store for hospital knowledge base.
    Supports adding, searching, and persisting knowledge embeddings.
    """

    def __init__(self, index_path: str = "./data/faiss_index"):
        self.index_path = index_path
        self.metadata_path = os.path.join(index_path, "metadata.json")
        self.index_file = os.path.join(index_path, "index.faiss")
        self.dimension = 384  # MiniLM-L6-v2 output dimension
        self.index = None
        self.metadata: List[Dict] = []
        self._embedder = None

    def _get_embedder(self):
        """Lazy-load the sentence transformer model"""
        if self._embedder is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._embedder = SentenceTransformer("all-MiniLM-L6-v2")
                logger.info("Loaded embedding model: all-MiniLM-L6-v2")
            except ImportError:
                logger.warning("sentence-transformers not available, using random embeddings for dev")
                self._embedder = "fallback"
        return self._embedder

    def _embed(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for text list"""
        embedder = self._get_embedder()
        if embedder == "fallback":
            # Deterministic fallback for development without ML deps
            return np.random.RandomState(42).randn(len(texts), self.dimension).astype("float32")
        return embedder.encode(texts, normalize_embeddings=True, show_progress_bar=False)

    def initialize(self):
        """Initialize or load existing FAISS index"""
        import faiss

        os.makedirs(self.index_path, exist_ok=True)

        if os.path.exists(self.index_file) and os.path.exists(self.metadata_path):
            self.index = faiss.read_index(self.index_file)
            with open(self.metadata_path, "r") as f:
                self.metadata = json.load(f)
            logger.info(f"Loaded FAISS index with {self.index.ntotal} vectors")
        else:
            self.index = faiss.IndexFlatIP(self.dimension)  # Inner product (cosine similarity with normalized vectors)
            self.metadata = []
            logger.info("Created new FAISS index")

    def add_documents(self, chunks: List[KnowledgeChunk]):
        """Add knowledge chunks to the vector store"""
        if not chunks:
            return

        import faiss

        if self.index is None:
            self.initialize()

        texts = [f"{c.title}\n{c.content}" for c in chunks]
        embeddings = self._embed(texts)

        self.index.add(embeddings.astype("float32"))

        for chunk in chunks:
            self.metadata.append({
                "id": chunk.id,
                "title": chunk.title,
                "content": chunk.content,
                "category": chunk.category,
            })

        self._save()
        logger.info(f"Added {len(chunks)} documents to vector store (total: {self.index.ntotal})")

    def search(self, query: str, top_k: int = 5, category: Optional[str] = None) -> List[Dict]:
        """Search for relevant knowledge chunks"""
        if self.index is None or self.index.ntotal == 0:
            return []

        query_embedding = self._embed([query]).astype("float32")
        scores, indices = self.index.search(query_embedding, min(top_k * 3, self.index.ntotal))

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self.metadata):
                continue
            meta = self.metadata[idx]
            if category and meta.get("category") != category:
                continue
            results.append({
                **meta,
                "score": float(score),
            })
            if len(results) >= top_k:
                break

        return results

    def _save(self):
        """Persist index and metadata to disk"""
        import faiss

        os.makedirs(self.index_path, exist_ok=True)
        faiss.write_index(self.index, self.index_file)
        with open(self.metadata_path, "w") as f:
            json.dump(self.metadata, f, indent=2)
        logger.info("Saved FAISS index to disk")

    def clear(self):
        """Clear the entire vector store"""
        import faiss

        self.index = faiss.IndexFlatIP(self.dimension)
        self.metadata = []
        self._save()
        logger.info("Cleared vector store")

    @property
    def total_documents(self) -> int:
        return self.index.ntotal if self.index else 0


# Global vector store instance
vector_store = VectorStore()
