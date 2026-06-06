import asyncio
import logging
from typing import List
from app.domain.repositories import IEmbeddingProvider

logger = logging.getLogger(__name__)


class SentenceTransformersEmbeddingProvider(IEmbeddingProvider):
    """Generates text embeddings using sentence-transformers model (BAAI/bge-large-en-v1.5)."""

    def __init__(self, model_name: str = "BAAI/bge-large-en-v1.5"):
        self.model_name = model_name
        self._model = None

    def _get_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading sentence-transformer model: {self.model_name}")
            self._model = SentenceTransformer(self.model_name)
            logger.info("Model loaded successfully")
        return self._model


    def _embed_text(self, text: str) -> List[float]:
        model = self._get_model()
        # BGE v1.5 recommends normalization
        embedding = model.encode(text, normalize_embeddings=True)
        return embedding.tolist()

    def _embed_batch(self, texts: List[str]) -> List[List[float]]:
        model = self._get_model()
        embeddings = model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()

    async def embed_text(self, text: str, is_query: bool = False) -> List[float]:
        """Generates embedding for a single text string."""
        if is_query:
            # Prefix for BGE v1.5 queries
            text = f"Represent this sentence for searching relevant passages: {text}"
        return await asyncio.to_thread(self._embed_text, text)

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generates embeddings for a list of text strings in batch."""
        return await asyncio.to_thread(self._embed_batch, texts)
