import base64
import os

import numpy as np
import pytest
from fastapi.testclient import TestClient
from huggingface_hub import try_to_load_from_cache
from sqlmodel import SQLModel

from lenzr_server.db import engine
from lenzr_server.embedding import (
    DEFAULT_LOCAL_MODEL,
    DEFAULT_SIMILARITY_THRESHOLD,
    TagEmbeddingIndex,
    load_static_model,
)
from lenzr_server.main import app
from lenzr_server.search_service import SearchService

E0 = [1.0, 0.0]


def _at_cosine(cosine: float) -> list[float]:
    """A unit vector whose cosine similarity with E0 is exactly `cosine`."""
    return [cosine, float(np.sqrt(1.0 - cosine * cosine))]


class FakeEncoder:
    """Maps text to a fixed vector; unknown text encodes to zeros."""

    def __init__(self, vectors_by_text: dict[str, list[float]]):
        self._vectors_by_text = vectors_by_text
        self.calls: list[tuple[list[str], bool]] = []

    def encode(self, texts, use_multiprocessing=True):
        self.calls.append((list(texts), use_multiprocessing))
        vectors = [self._vectors_by_text.get(text, [0.0, 0.0]) for text in texts]
        return np.asarray(vectors, dtype=np.float32)


def _service(database_session, vectors_by_text, threshold: float = 0.5) -> SearchService:
    index = TagEmbeddingIndex(FakeEncoder(vectors_by_text), similarity_threshold=threshold)
    return SearchService(database_session=database_session, tag_embedding_index=index)


def test__search__semantic_match_found_above_threshold(add_upload, database_session):
    add_upload("u-sea", ["sea"])
    service = _service(database_session, {"ocean": E0, "sea": _at_cosine(0.8)})

    results = service.search("ocean")

    assert results.semantic_status == "active"
    assert results.total_count == 1
    match = results.items[0].matches[0]
    assert match.matched_tag == "sea"
    assert match.match_type == "semantic"
    assert match.score == pytest.approx(0.8, abs=1e-6)


def test__search__semantic_ranks_below_fuzzy_for_same_query(add_upload, database_session):
    add_upload("u-fuzzy", ["lanscape"])
    add_upload("u-semantic", ["scenery"])
    service = _service(database_session, {"landscape": E0, "scenery": _at_cosine(0.9)})

    results = service.search("landscape")

    assert [item.upload.upload_id for item in results.items] == ["u-fuzzy", "u-semantic"]
    assert [item.matches[0].match_type for item in results.items] == ["fuzzy", "semantic"]


def test__search__cosine_below_threshold__excluded(add_upload, database_session):
    add_upload("u-far", ["keyboard"])
    service = _service(database_session, {"ocean": E0, "keyboard": _at_cosine(0.4)})

    results = service.search("ocean")

    assert results.total_count == 0
    assert results.semantic_status == "active"


def test__search__top_k_caps_semantic_candidates_per_term(add_upload, database_session):
    vectors = {"ocean": E0}
    for i in range(11):
        add_upload(f"u{i}", [f"tag-{i}"])
        vectors[f"tag-{i}"] = _at_cosine(0.99 - i * 0.01)
    service = _service(database_session, vectors)

    results = service.search("ocean", limit=100)

    assert results.total_count == 10
    assert "u10" not in {item.upload.upload_id for item in results.items}


def test__search__weakest_link__exact_plus_semantic_ranks_below_fully_lexical(
    add_upload, database_session
):
    add_upload("u-lexical", ["ocean", "sunset"])
    add_upload("u-mixed", ["ocean", "dusk"], hour=1)
    service = _service(database_session, {"sunset": E0, "dusk": _at_cosine(0.9)})

    results = service.search("ocean sunset")

    assert [item.upload.upload_id for item in results.items] == ["u-lexical", "u-mixed"]
    assert [m.match_type for m in results.items[1].matches] == ["exact", "semantic"]


def test__search__lexical_tier_wins_over_semantic_for_same_tag(add_upload, database_session):
    add_upload("u1", ["ocean"])
    service = _service(database_session, {"ocean": E0})

    match = service.search("ocean").items[0].matches[0]

    assert match.match_type == "exact"
    assert match.score == 1.0


def test__search__tag_added_after_first_search__is_found(add_upload, database_session):
    service = _service(database_session, {"ocean": E0, "sea": _at_cosine(0.8)})
    assert service.search("ocean").total_count == 0

    add_upload("u-sea", ["sea"])

    assert service.search("ocean").total_count == 1


def test__search__all_short_terms__no_encode_call_and_status_active(add_upload, database_session):
    add_upload("u1", ["ab"])
    encoder = FakeEncoder({})
    index = TagEmbeddingIndex(encoder, similarity_threshold=0.5)
    service = SearchService(database_session=database_session, tag_embedding_index=index)

    results = service.search("ab")

    assert encoder.calls == []
    assert results.semantic_status == "active"
    assert results.total_count == 1


def test__index__normalizes_vectors():
    index = TagEmbeddingIndex(FakeEncoder({"ocean": [3.0, 0.0], "sea": [7.0, 0.0]}), 0.5)

    assert index.similar_tags(["ocean"], ["sea"], top_k=10) == {
        "ocean": [("sea", pytest.approx(1.0))]
    }


def test__index__zero_vectors_never_match():
    index = TagEmbeddingIndex(FakeEncoder({"ocean": E0}), 0.5)

    assert index.similar_tags(["ocean"], ["unknown"], top_k=10) == {"ocean": []}


def test__index__reencodes_vocabulary_only_when_it_changes():
    encoder = FakeEncoder({})
    index = TagEmbeddingIndex(encoder, 0.5)

    index.similar_tags(["ocean"], ["sea"], top_k=10)
    index.similar_tags(["ocean"], ["sea"], top_k=10)
    index.similar_tags(["ocean"], ["sea", "shore"], top_k=10)
    index.similar_tags(["ocean"], ["shore", "sea"], top_k=10)

    assert encoder.calls == [
        (["sea"], False),
        (["ocean"], False),
        (["ocean"], False),
        (["sea", "shore"], False),
        (["ocean"], False),
        (["ocean"], False),
    ]


def test__index__empty_vocabulary__no_encode_call():
    encoder = FakeEncoder({})

    assert TagEmbeddingIndex(encoder, 0.5).similar_tags(["ocean"], [], top_k=10) == {"ocean": []}
    assert encoder.calls == []


@pytest.mark.skipif(
    not isinstance(try_to_load_from_cache(DEFAULT_LOCAL_MODEL, "model.safetensors"), str),
    reason=f"{DEFAULT_LOCAL_MODEL} not in the local HF cache; CI never downloads",
)
def test__index__real_model__ocean_is_similar_to_sea():
    index = TagEmbeddingIndex(load_static_model(DEFAULT_LOCAL_MODEL), DEFAULT_SIMILARITY_THRESHOLD)

    [(tag, _)] = index.similar_tags(["ocean"], ["sea", "invoice"], top_k=10)["ocean"]

    assert tag == "sea"


def test__api_search__end_to_end__semantic_match(mocker):
    encoder = FakeEncoder({"sea": E0, "ocean": _at_cosine(0.8)})
    mocker.patch("lenzr_server.embedding.factory.load_static_model", return_value=encoder)
    # Must be set before TestClient enters the lifespan.
    mocker.patch.dict(
        os.environ, {"EMBEDDING_PROVIDER": "local", "SEMANTIC_SIMILARITY_THRESHOLD": "0.5"}
    )
    headers = {"Authorization": f"Basic {base64.b64encode(b'test_user:test_pass').decode()}"}

    SQLModel.metadata.create_all(engine)
    try:
        with TestClient(app) as client:
            response = client.post(
                "/uploads",
                files={"upload": ("test.png", b"semantic e2e", "image/png")},
                params={"tags": ["sea"]},
                headers=headers,
            )
            upload_id = response.json()["upload_id"]

            response = client.get("/uploads/search", params={"q": "ocean"}, headers=headers)

            assert response.status_code == 200
            body = response.json()
            assert body["semantic_status"] == "active"
            assert body["total_count"] == 1
            result = body["results"][0]
            assert result["upload_id"] == upload_id
            assert result["matches"] == [
                {
                    "term": "ocean",
                    "matched_tag": "sea",
                    "match_type": "semantic",
                    "score": pytest.approx(0.8, abs=1e-6),
                }
            ]
    finally:
        SQLModel.metadata.drop_all(engine)
