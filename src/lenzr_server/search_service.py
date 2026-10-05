import unicodedata
import uuid
from collections import defaultdict
from dataclasses import dataclass
from typing import NamedTuple, get_args

from rapidfuzz.distance import Levenshtein
from sqlmodel import Session, col, select

from lenzr_server.exceptions import InvalidSearchQueryException
from lenzr_server.models.tags import Tag, UploadTag
from lenzr_server.models.uploads import UploadMetaData
from lenzr_server.tag_service import TagService, UploadWithTags
from lenzr_server.types import MatchType, SemanticStatus, TagName

MAX_QUERY_LENGTH = 256
MAX_TERMS = 5
MIN_TERM_LENGTH_FOR_DEEP_TIERS = 3

_TIER: dict[MatchType, int] = {
    match_type: tier for tier, match_type in enumerate(get_args(MatchType))
}


class Candidate(NamedTuple):
    match_type: MatchType
    score: float


Candidates = dict[TagName, Candidate]


def normalize_query(q: str) -> list[str]:
    """Split q into unique [a-z0-9-] terms; raise if none or more than MAX_TERMS remain."""
    terms: list[str] = []
    for raw_term in q.lower().split():
        folded = unicodedata.normalize("NFKD", raw_term).encode("ascii", "ignore").decode("ascii")
        term = "".join(c for c in folded if "a" <= c <= "z" or "0" <= c <= "9" or c == "-")
        if term:
            terms.append(term)

    unique_terms = list(dict.fromkeys(terms))
    if not unique_terms:
        raise InvalidSearchQueryException("Query contains no searchable terms")
    if len(unique_terms) > MAX_TERMS:
        raise InvalidSearchQueryException(f"Query contains more than {MAX_TERMS} terms")
    return unique_terms


def _fuzzy_max_edits(term: str) -> int:
    # Length-scaled edit distance (Elasticsearch AUTO convention).
    return 1 if len(term) <= 5 else 2


def _match_term(term: str, vocabulary: list[TagName]) -> Candidates:
    """Map each matching tag to its best tier; short terms only match exact and prefix."""
    run_deep_tiers = len(term) >= MIN_TERM_LENGTH_FOR_DEEP_TIERS
    max_edits = _fuzzy_max_edits(term)
    candidates: Candidates = {}
    for tag in vocabulary:
        if tag == term:
            candidates[tag] = Candidate("exact", 1.0)
        elif tag.startswith(term):
            candidates[tag] = Candidate("prefix", 1.0)
        elif run_deep_tiers and term in tag:
            candidates[tag] = Candidate("substring", 1.0)
        elif (
            run_deep_tiers and Levenshtein.distance(term, tag, score_cutoff=max_edits) <= max_edits
        ):
            candidates[tag] = Candidate("fuzzy", Levenshtein.normalized_similarity(term, tag))
    return candidates


@dataclass
class TermMatch:
    term: str
    matched_tag: TagName
    match_type: MatchType
    score: float


@dataclass
class QualifyingUpload:
    upload: UploadMetaData
    matches: list[TermMatch]


@dataclass
class SearchResultItem:
    upload: UploadWithTags
    matches: list[TermMatch]  # one per query term, in query-term order


@dataclass
class SearchResults:
    items: list[SearchResultItem]  # the requested page
    total_count: int
    semantic_status: SemanticStatus


def _rank(item: QualifyingUpload) -> tuple[int, int, float, float]:
    tiers = [_TIER[match.match_type] for match in item.matches]
    mean_score = sum(match.score for match in item.matches) / len(item.matches)
    # Weakest link first, then tier sum, mean score and recency.
    return max(tiers), sum(tiers), -mean_score, -item.upload.created_at.timestamp()


class SearchService:
    def __init__(self, database_session: Session):
        self._database_session = database_session
        self._tag_service = TagService(database_session)

    def search(self, q: str, offset: int = 0, limit: int = 10) -> SearchResults:
        terms = normalize_query(q)
        vocabulary = list(self._database_session.exec(select(Tag.name)).all())
        candidates_by_term = {term: _match_term(term, vocabulary) for term in terms}
        semantic_status: SemanticStatus = "disabled"

        if any(not candidates for candidates in candidates_by_term.values()):
            # AND semantics: a term without any candidate tag can never match.
            return SearchResults(items=[], total_count=0, semantic_status=semantic_status)

        ranked = sorted(self._qualifying_uploads(terms, candidates_by_term), key=_rank)
        page = ranked[offset : offset + limit]
        uploads = self._tag_service.to_uploads_with_tags([item.upload for item in page])
        return SearchResults(
            items=[
                SearchResultItem(upload=upload, matches=item.matches)
                for upload, item in zip(uploads, page, strict=True)
            ],
            total_count=len(ranked),
            semantic_status=semantic_status,
        )

    def _qualifying_uploads(
        self,
        terms: list[str],
        candidates_by_term: dict[str, Candidates],
    ) -> list[QualifyingUpload]:
        """Resolve candidate tags to uploads and evaluate the AND across terms."""
        all_candidate_tags = {tag for c in candidates_by_term.values() for tag in c}
        rows = self._database_session.exec(
            select(UploadMetaData, Tag.name)
            .join(UploadTag, col(UploadTag.upload_pk) == UploadMetaData.pk)
            .join(Tag, col(Tag.pk) == UploadTag.tag_pk)
            .where(col(Tag.name).in_(all_candidate_tags))
        ).all()

        uploads_by_pk: dict[uuid.UUID | None, UploadMetaData] = {}
        candidate_tags_by_pk: defaultdict[uuid.UUID | None, set[TagName]] = defaultdict(set)
        for upload, tag_name in rows:
            uploads_by_pk[upload.pk] = upload
            candidate_tags_by_pk[upload.pk].add(tag_name)

        qualifying: list[QualifyingUpload] = []
        for pk, upload in uploads_by_pk.items():
            matches = self._best_matches(terms, candidates_by_term, candidate_tags_by_pk[pk])
            if matches is not None:
                qualifying.append(QualifyingUpload(upload=upload, matches=matches))
        return qualifying

    @staticmethod
    def _best_matches(
        terms: list[str],
        candidates_by_term: dict[str, Candidates],
        upload_tags: set[TagName],
    ) -> list[TermMatch] | None:
        """Best match per term among the upload's tags; None if a term has none."""
        matches: list[TermMatch] = []
        for term in terms:
            candidates = candidates_by_term[term]
            tags = upload_tags & candidates.keys()
            if not tags:
                return None
            tag = min(
                tags, key=lambda t: (_TIER[candidates[t].match_type], -candidates[t].score, t)
            )
            match_type, score = candidates[tag]
            matches.append(
                TermMatch(term=term, matched_tag=tag, match_type=match_type, score=score)
            )
        return matches
