from lenzr_server.embedding.factory import (
    DEFAULT_LOCAL_MODEL,
    DEFAULT_SIMILARITY_THRESHOLD,
    load_static_model,
    tag_embedding_index_from_env,
)
from lenzr_server.embedding.index import TagEmbeddingIndex

__all__ = [
    "DEFAULT_LOCAL_MODEL",
    "DEFAULT_SIMILARITY_THRESHOLD",
    "TagEmbeddingIndex",
    "load_static_model",
    "tag_embedding_index_from_env",
]
