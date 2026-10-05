import pytest

from lenzr_server.embedding import (
    DEFAULT_LOCAL_MODEL,
    TagEmbeddingIndex,
    tag_embedding_index_from_env,
)


@pytest.fixture
def load_static_model(mocker):
    return mocker.patch("lenzr_server.embedding.factory.load_static_model")


def test__index_from_env__provider_unset__returns_none(load_static_model):
    assert tag_embedding_index_from_env() is None
    load_static_model.assert_not_called()


def test__index_from_env__invalid_provider__raises_value_error(monkeypatch):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "sidecar")

    with pytest.raises(ValueError, match="EMBEDDING_PROVIDER"):
        tag_embedding_index_from_env()


def test__index_from_env__local__loads_default_model(monkeypatch, load_static_model):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "local")

    assert isinstance(tag_embedding_index_from_env(), TagEmbeddingIndex)
    load_static_model.assert_called_once_with(DEFAULT_LOCAL_MODEL)


def test__index_from_env__local__loads_configured_model(monkeypatch, load_static_model):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "local")
    monkeypatch.setenv("EMBEDDING_LOCAL_MODEL", "/models/custom")

    tag_embedding_index_from_env()

    load_static_model.assert_called_once_with("/models/custom")


def test__index_from_env__non_float_threshold__raises_value_error(monkeypatch):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "local")
    monkeypatch.setenv("SEMANTIC_SIMILARITY_THRESHOLD", "very high")

    with pytest.raises(ValueError, match="SEMANTIC_SIMILARITY_THRESHOLD"):
        tag_embedding_index_from_env()


def test__index_from_env__model_load_failure__returns_none(monkeypatch, load_static_model):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "local")
    load_static_model.side_effect = OSError("model not in cache")

    assert tag_embedding_index_from_env() is None
