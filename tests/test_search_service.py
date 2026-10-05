import pytest

from lenzr_server.exceptions import InvalidSearchQueryException
from lenzr_server.search_service import (
    SearchResults,
    SearchService,
    normalize_query,
)
from lenzr_server.tag_service import TagService


def _result_ids(results: SearchResults) -> list[str]:
    return [item.upload.upload_id for item in results.items]


@pytest.fixture
def search_service(database_session) -> SearchService:
    return SearchService(database_session=database_session)


@pytest.mark.parametrize(
    ("query", "terms"),
    [
        pytest.param("CôTe", ["cote"], id="case_and_accents_folded"),
        pytest.param("sun,set! beach?", ["sunset", "beach"], id="punctuation_stripped"),
        pytest.param("ocean-sunset", ["ocean-sunset"], id="hyphen_preserved"),
        pytest.param("Cat cat dog", ["cat", "dog"], id="duplicates_deduped"),
        pytest.param("a b c d e a", ["a", "b", "c", "d", "e"], id="five_terms_after_dedupe"),
    ],
)
def test__normalize_query__valid__returns_terms(query, terms):
    assert normalize_query(query) == terms


@pytest.mark.parametrize("query", ["a b c d e f", "!!! ???"], ids=["six_terms", "no_terms"])
def test__normalize_query__invalid__raises(query):
    with pytest.raises(InvalidSearchQueryException):
        normalize_query(query)


def test__search__tier_ordering__exact_beats_prefix_beats_substring_beats_fuzzy(
    add_upload, search_service
):
    add_upload("u-exact", ["land"])
    add_upload("u-prefix", ["landscape"])
    add_upload("u-substring", ["inland"])
    add_upload("u-fuzzy", ["lend"])

    results = search_service.search("land")

    assert _result_ids(results) == ["u-exact", "u-prefix", "u-substring", "u-fuzzy"]
    match_types = [item.matches[0].match_type for item in results.items]
    assert match_types == ["exact", "prefix", "substring", "fuzzy"]


def test__search__exact_scores_one__fuzzy_scores_below_one(add_upload, search_service):
    add_upload("u-exact", ["land"])
    add_upload("u-fuzzy", ["lend"])

    results = search_service.search("land")

    by_id = {item.upload.upload_id: item for item in results.items}
    assert by_id["u-exact"].matches[0].score == 1.0
    assert 0.0 < by_id["u-fuzzy"].matches[0].score < 1.0


def test__search__short_term__runs_exact_and_prefix_only(add_upload, search_service):
    add_upload("u-exact", ["se"])
    add_upload("u-prefix", ["sea"])
    add_upload("u-substring", ["base"])  # would match "se" as substring
    add_upload("u-fuzzy", ["so"])  # 1 edit from "se"

    results = search_service.search("se")

    assert _result_ids(results) == ["u-exact", "u-prefix"]


@pytest.mark.parametrize(
    ("tag", "query", "matches"),
    [
        pytest.param("cat", "cot", True, id="one_edit_short_term"),
        pytest.param("bat", "cot", False, id="two_edits_short_term"),
        pytest.param("landscape", "lanscap", True, id="two_edits_long_term"),
        pytest.param("landscape", "lnscpe", False, id="three_edits_long_term"),
    ],
)
def test__search__fuzzy__edit_limit_scales_with_term_length(
    add_upload, search_service, tag, query, matches
):
    add_upload("u1", [tag])

    results = search_service.search(query)

    match_types = [match.match_type for item in results.items for match in item.matches]
    assert match_types == (["fuzzy"] if matches else [])


def test__search__multi_term__upload_must_match_every_term(add_upload, search_service):
    add_upload("u-both", ["ocean", "sunset"])
    add_upload("u-one", ["ocean"])

    results = search_service.search("ocean sunset")

    assert _result_ids(results) == ["u-both"]


def test__search__multi_term__weakest_link_ranks_below_fully_exact(add_upload, search_service):
    add_upload("u-weak", ["ocean", "sunsets"])
    add_upload("u-exact", ["ocean", "sunset"], hour=-1)

    results = search_service.search("ocean sunset")

    assert _result_ids(results) == ["u-exact", "u-weak"]
    assert [m.match_type for m in results.items[1].matches] == ["exact", "prefix"]


def test__search__multi_term__sum_of_tiers_breaks_max_tier_tie(add_upload, search_service):
    # Both weakest at fuzzy ("dog" -> "dot"); exact "cat" beats substring "scat".
    add_upload("u-low-sum", ["cat", "dot"])
    add_upload("u-high-sum", ["scat", "dot"], hour=1)

    results = search_service.search("cat dog")

    assert _result_ids(results) == ["u-low-sum", "u-high-sum"]


def test__search__mean_score_breaks_tier_sum_tie(add_upload, search_service):
    # Both fuzzy: distance 1 scores higher than distance 2.
    add_upload("u-closer", ["lanscape"])
    add_upload("u-farther", ["lanscap"], hour=1)

    results = search_service.search("landscape")

    assert _result_ids(results) == ["u-closer", "u-farther"]


def test__search__created_at_desc_is_final_tie_break(add_upload, search_service):
    add_upload("u-old", ["cat"])
    add_upload("u-new", ["cat"], hour=1)

    results = search_service.search("cat")

    assert _result_ids(results) == ["u-new", "u-old"]


def test__search__upload_matching_term_via_multiple_tags__appears_once_with_best_match(
    add_upload, search_service
):
    add_upload("u1", ["land", "landscape"])

    results = search_service.search("land")

    assert results.total_count == 1
    matches = results.items[0].matches
    assert len(matches) == 1
    assert matches[0].matched_tag == "land"
    assert matches[0].match_type == "exact"


def test__search__matches_are_in_query_term_order(add_upload, search_service):
    add_upload("u1", ["sunset", "ocean"])

    results = search_service.search("ocean sunset")

    assert [match.term for match in results.items[0].matches] == ["ocean", "sunset"]


def test__search__term_without_any_candidate__returns_empty(add_upload, search_service):
    add_upload("u1", ["ocean"])

    results = search_service.search("ocean zzzzzz")

    assert results.items == []
    assert results.total_count == 0


def test__search__no_tags_at_all__returns_empty(search_service):
    results = search_service.search("ocean")

    assert results.items == []
    assert results.total_count == 0


def test__search__no_embedding_index__semantic_status_disabled(add_upload, search_service):
    add_upload("u1", ["ocean"])

    results = search_service.search("ocean")

    assert results.semantic_status == "disabled"


def test__search__result_carries_full_tag_list(add_upload, search_service):
    add_upload("u1", ["ocean", "sunset", "beach"])

    results = search_service.search("ocean")

    assert sorted(results.items[0].upload.tags) == ["beach", "ocean", "sunset"]


def test__search__pagination__total_count_reflects_full_set(add_upload, search_service):
    for i in range(5):
        add_upload(f"u{i}", ["cat"], hour=i)

    results = search_service.search("cat", offset=1, limit=2)

    assert results.total_count == 5
    # Full order is u4..u0 (created_at DESC); offset 1, limit 2 -> u3, u2.
    assert _result_ids(results) == ["u3", "u2"]


def test__search__pagination__loads_tags_for_the_page_only(add_upload, search_service, mocker):
    for i in range(5):
        add_upload(f"u{i}", ["cat"], hour=i)
    to_uploads_with_tags = mocker.spy(TagService, "to_uploads_with_tags")

    search_service.search("cat", offset=1, limit=2)

    [call] = to_uploads_with_tags.call_args_list
    assert [upload.upload_id for upload in call.args[1]] == ["u3", "u2"]


def test__search__pagination__offset_beyond_set__returns_empty_with_total(
    add_upload, search_service
):
    add_upload("u1", ["cat"])

    results = search_service.search("cat", offset=10, limit=10)

    assert results.items == []
    assert results.total_count == 1
