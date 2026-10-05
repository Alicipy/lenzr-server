from typing import Protocol

import numpy as np


class TextEncoder(Protocol):
    def encode(self, sentences: list[str], /, *, use_multiprocessing: bool) -> np.ndarray: ...


class TagEmbeddingIndex:
    """In-memory unit-length embeddings of the tag vocabulary, rebuilt when it changes."""

    def __init__(self, encoder: TextEncoder, similarity_threshold: float):
        self._encoder = encoder
        self._similarity_threshold = similarity_threshold
        self._cache: tuple[list[str], np.ndarray] = ([], np.empty((0, 0), dtype=np.float32))

    def similar_tags(
        self, terms: list[str], vocabulary: list[str], *, top_k: int
    ) -> dict[str, list[tuple[str, float]]]:
        """Up to top_k tags per term whose cosine similarity reaches the threshold."""
        if not terms or not vocabulary:
            return {term: [] for term in terms}
        vocabulary = sorted(vocabulary)
        cached_vocabulary, matrix = self._cache
        if vocabulary != cached_vocabulary:
            matrix = self._embed(vocabulary)
            self._cache = (vocabulary, matrix)
        similarities = self._embed(terms) @ matrix.T
        return {
            term: [
                (vocabulary[i], float(row[i]))
                for i in np.argsort(row)[::-1][:top_k]
                if row[i] >= self._similarity_threshold
            ]
            for term, row in zip(terms, similarities, strict=True)
        }

    def _embed(self, texts: list[str]) -> np.ndarray:
        vectors = np.asarray(self._encoder.encode(texts, use_multiprocessing=False), np.float32)
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        return np.divide(vectors, norms, out=np.zeros_like(vectors), where=norms > 0)
