from __future__ import annotations

import datetime
from dataclasses import asdict
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

from lenzr_server.models.uploads import UploadMetaDataBase
from lenzr_server.types import MatchType, SemanticStatus, TagName, UploadID

if TYPE_CHECKING:
    from lenzr_server.search_service import SearchResultItem, SearchResults, TermMatch
    from lenzr_server.tag_service import UploadWithTags


class UploadMetaDataCreateResponse(UploadMetaDataBase):
    tags: list[TagName] = []


class UploadMetaDataPublicResponse(UploadMetaDataBase):
    pass


class UploadMetaDataDeleteResponse(UploadMetaDataBase):
    pass


class ErrorResponse(BaseModel):
    detail: str

    model_config = ConfigDict(json_schema_extra={"example": {"detail": "Upload not found"}})


class TagsUpdateRequest(BaseModel):
    tags: list[TagName]


class UploadWithTagsResponse(BaseModel):
    upload_id: UploadID
    tags: list[TagName]
    created_at: datetime.datetime
    content_type: str

    @classmethod
    def from_upload_with_tags(cls, uwt: UploadWithTags) -> UploadWithTagsResponse:
        return cls(
            upload_id=uwt.upload_id,
            tags=uwt.tags,
            created_at=uwt.created_at,
            content_type=uwt.content_type,
        )


class TagListResponse(BaseModel):
    tags: list[TagName]


_SCORED_MATCH_TYPES: frozenset[MatchType] = frozenset({"fuzzy", "semantic"})


class SearchMatchResponse(BaseModel):
    term: str
    matched_tag: TagName
    match_type: MatchType
    score: float | None = None

    @classmethod
    def from_term_match(cls, match: TermMatch) -> SearchMatchResponse:
        return cls(
            term=match.term,
            matched_tag=match.matched_tag,
            match_type=match.match_type,
            score=match.score if match.match_type in _SCORED_MATCH_TYPES else None,
        )


class SearchResultItemResponse(UploadWithTagsResponse):
    matches: list[SearchMatchResponse]

    @classmethod
    def from_search_result_item(cls, item: SearchResultItem) -> SearchResultItemResponse:
        return cls(
            **asdict(item.upload),
            matches=[SearchMatchResponse.from_term_match(match) for match in item.matches],
        )


class SearchResponse(BaseModel):
    results: list[SearchResultItemResponse]
    total_count: int
    semantic_status: SemanticStatus

    @classmethod
    def from_search_results(cls, search_results: SearchResults) -> SearchResponse:
        return cls(
            results=[
                SearchResultItemResponse.from_search_result_item(item)
                for item in search_results.items
            ],
            total_count=search_results.total_count,
            semantic_status=search_results.semantic_status,
        )
