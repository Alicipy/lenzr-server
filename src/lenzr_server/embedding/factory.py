import logging
import os
from typing import TYPE_CHECKING

from lenzr_server.embedding.index import TagEmbeddingIndex

if TYPE_CHECKING:
    from model2vec import StaticModel

# The threshold is model-relative: re-derive it when changing the model.
DEFAULT_LOCAL_MODEL = "minishlab/potion-base-8M"
DEFAULT_SIMILARITY_THRESHOLD = 0.23


def load_static_model(model_id: str) -> "StaticModel":
    # Lazy import keeps model2vec off the startup path when semantic search is off.
    from model2vec import StaticModel

    return StaticModel.from_pretrained(model_id, force_download=False)


def _similarity_threshold_from_env() -> float:
    raw_threshold = os.getenv("SEMANTIC_SIMILARITY_THRESHOLD")
    if not raw_threshold:
        return DEFAULT_SIMILARITY_THRESHOLD
    try:
        return float(raw_threshold)
    except ValueError:
        raise ValueError(
            f"Invalid SEMANTIC_SIMILARITY_THRESHOLD: must be a float, got: {raw_threshold}"
        ) from None


def tag_embedding_index_from_env() -> TagEmbeddingIndex | None:
    provider = os.getenv("EMBEDDING_PROVIDER") or "none"
    if provider == "none":
        return None
    if provider != "local":
        raise ValueError(f"Invalid EMBEDDING_PROVIDER: must be none or local, got: {provider}")

    similarity_threshold = _similarity_threshold_from_env()
    model_id = os.getenv("EMBEDDING_LOCAL_MODEL") or DEFAULT_LOCAL_MODEL
    logging.info("Loading embedding model %s", model_id)
    try:
        model = load_static_model(model_id)
    except OSError:
        logging.exception("Failed to load embedding model %s; semantic search disabled", model_id)
        return None
    return TagEmbeddingIndex(model, similarity_threshold)
