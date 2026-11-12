"""Portal catalog search ranking."""

import pytest

from services.portal import discover_details


class _FakeResponse:
    def __init__(self, results):
        self._results = results

    def json(self):
        return {"results": self._results}


class _FakeTmdbClient:
    def __init__(self):
        self.queries = []
        self.languages = []

    async def get(self, _url, *, params, headers):
        self.queries.append(params["query"])
        self.languages.append(params["language"])
        if params["query"] == "enquet criminellle":
            return _FakeResponse([
                _tmdb_movie(10, "Enquete de voisinage", popularity=95),
            ])
        if params["query"] == "enquetes criminelles":
            return _FakeResponse([
                _tmdb_movie(20, "Enquêtes criminelles", popularity=4),
            ])
        if params["query"] == "enquete criminel":
            return _FakeResponse([
                _tmdb_movie(10, "Enquete de voisinage", popularity=95),
            ])
        if params["query"] == "Enquete criminelle":
            return _FakeResponse([
                _tmdb_movie(10, "Enquete de voisinage", popularity=95),
            ])
        if params["query"] == "Enquetes criminelles":
            return _FakeResponse([
                _tmdb_movie(20, "Enquêtes criminelles", popularity=4),
            ])
        if params["query"] == "enquetescriminelles":
            return _FakeResponse([
                _tmdb_movie(10, "Enquete de voisinage", popularity=95),
            ])
        if params["query"] == "criminal investigattion":
            return _FakeResponse([
                _tmdb_movie(30, "Criminal Confession", popularity=80),
            ])
        if params["query"] == "criminal investigation":
            return _FakeResponse([
                _tmdb_movie(40, "Criminal Investigation", popularity=6),
            ])
        if params["query"] == "ironknight":
            return _FakeResponse([
                _tmdb_movie(80, "Ironworks", popularity=90),
            ])
        if params["query"] == "iron knight":
            return _FakeResponse([
                _tmdb_movie(70, "Iron-Knight", popularity=15),
            ])
        if params["query"] == "ghostmission":
            return _FakeResponse([
                _tmdb_movie(81, "Ghost Control", popularity=90),
            ])
        if params["query"] == "ghost mission":
            return _FakeResponse([
                _tmdb_movie(71, "Ghost: Mission", popularity=15),
            ])
        return _FakeResponse([])


def _tmdb_movie(tmdb_id, title, *, popularity=0, year=2024):
    return {
        "id": tmdb_id,
        "media_type": "movie",
        "title": title,
        "original_title": title,
        "release_date": f"{year}-01-01",
        "overview": "",
        "poster_path": "/poster.jpg",
        "backdrop_path": None,
        "vote_average": 7.1,
        "popularity": popularity,
        "genre_ids": [],
    }


def test_search_query_variants_cover_missing_plural_s():
    variants = discover_details._search_query_variants("Enquete criminelle")

    assert variants[0] == "Enquete criminelle"
    assert "Enquetes criminelles" in variants


def test_search_query_variants_cover_romance_gender_suffix():
    variants = discover_details._search_query_variants("enquete criminel")

    assert "enquete criminelle" in variants
    assert "enquetes criminelles" in variants


def test_search_query_variants_cover_small_typos():
    variants = discover_details._search_query_variants("enquet criminellle")

    assert "enquete criminelle" in variants
    assert "enquetes criminelles" in variants


def test_search_query_variants_cover_english_extra_letter():
    variants = discover_details._search_query_variants("criminal investigattion")

    assert "criminal investigation" in variants
    assert "criminals investigations" in variants


def test_search_query_variants_normalize_symbols_and_punctuation():
    assert "Iron Knight" in discover_details._search_query_variants("Iron-Knight")
    symbol_variants = discover_details._search_query_variants("ghost & dragon")
    assert "ghost and dragon" in symbol_variants
    assert "ghost dragon" in symbol_variants


def test_search_query_variants_split_missing_separators():
    assert "iron knight" in discover_details._search_query_variants("ironknight")
    assert "ant man" in discover_details._search_query_variants("antman")
    assert "x men" in discover_details._search_query_variants("xmen")
    assert "ghost mission" in discover_details._search_query_variants("ghostmission")
    assert "enquetes criminelles" in discover_details._search_query_variants("enquetescriminelles")
    assert "la casa de la peur" in discover_details._search_query_variants("lacasadelapeur")
    assert "the ghost and the dragon" in discover_details._search_query_variants("theghostandthedragon")
    assert "la cite du dragon" in discover_details._search_query_variants("lacitedudragon")
    assert "le grand criminel" in discover_details._search_query_variants("legrandcriminel")


def test_search_query_variants_keep_accentless_forms():
    variants = discover_details._search_query_variants("Enquête criminelle")

    assert "Enquête criminelle" in variants
    assert "Enquete criminelle" in variants
    assert "Enquêtes criminelles" in variants
    assert "Enquetes criminelles" in variants


def test_search_score_tolerates_german_diacritics():
    exact = discover_details._score_search_result(
        "Muller im Wald",
        _tmdb_movie(50, "Müller im Wald"),
        1,
        0,
    )
    partial = discover_details._score_search_result(
        "Muller im Wald",
        _tmdb_movie(60, "Der Wald am See", popularity=90),
        0,
        0,
    )

    assert exact > partial


def test_search_score_matches_compact_titles():
    exact = discover_details._score_search_result(
        "ironknight",
        _tmdb_movie(70, "Iron-Knight"),
        1,
        0,
    )
    partial = discover_details._score_search_result(
        "ironknight",
        _tmdb_movie(80, "Ironworks", popularity=90),
        0,
        0,
    )

    assert exact > partial


def test_search_score_uses_year_without_hurting_title_match():
    right_year = discover_details._score_search_result(
        "sample 2015",
        _tmdb_movie(90, "The Sample", popularity=30, year=2015),
        0,
        0,
    )
    wrong_year = discover_details._score_search_result(
        "sample 2015",
        _tmdb_movie(91, "The Sample Returns", popularity=90, year=2019),
        0,
        0,
    )

    assert right_year > wrong_year


def test_search_score_keeps_numbered_titles_logical():
    numbered_title = discover_details._score_search_result(
        "2042 space journey",
        _tmdb_movie(92, "2042: A Space Journey", popularity=30, year=1990),
        0,
        0,
    )
    wrong_title_with_matching_year = discover_details._score_search_result(
        "2042 space journey",
        _tmdb_movie(93, "Space Drifters", popularity=90, year=2042),
        0,
        0,
    )

    assert numbered_title > wrong_title_with_matching_year


def test_search_score_tolerates_small_typos():
    exact_plural = discover_details._score_search_result(
        "enquet criminellle",
        _tmdb_movie(20, "Enquêtes criminelles"),
        1,
        0,
    )
    partial = discover_details._score_search_result(
        "enquet criminellle",
        _tmdb_movie(10, "Enquete de voisinage", popularity=95),
        0,
        0,
    )

    assert exact_plural > partial


def test_search_score_ignores_accents_and_plural_s():
    exact_plural = discover_details._score_search_result(
        "Enquete criminelle",
        _tmdb_movie(20, "Enquêtes criminelles"),
        1,
        0,
    )
    partial = discover_details._score_search_result(
        "Enquete criminelle",
        _tmdb_movie(10, "Enquete de voisinage", popularity=95),
        0,
        0,
    )

    assert exact_plural > partial


def test_tmdb_language_uses_profile_region():
    assert discover_details._tmdb_language("en") == "en-US"
    assert discover_details._tmdb_language("de") == "de-DE"
    assert discover_details._tmdb_language("es") == "es-ES"
    assert discover_details._tmdb_language("fr-FR") == "fr-FR"


def test_search_languages_fallback_to_default_and_english():
    assert discover_details._search_languages("de") == ["de-DE", "fr-FR", "en-US"]
    assert discover_details._search_languages("en") == ["en-US", "fr-FR"]


@pytest.mark.asyncio
async def test_search_merges_variants_and_ranks_best_title_first(monkeypatch, db_session):
    client = _FakeTmdbClient()
    monkeypatch.setattr(discover_details._search, "get_external_client", lambda: client)

    async def fake_tmdb_key(_db):
        return "test-key"

    monkeypatch.setattr(discover_details._search, "_get_tmdb_key", fake_tmdb_key)

    items = await discover_details.search_tmdb_multi(
        db_session,
        "Enquete criminelle",
    )

    assert "Enquete criminelle" in client.queries
    assert "Enquetes criminelles" in client.queries
    assert [item["tmdb_id"] for item in items] == [20, 10]


@pytest.mark.asyncio
async def test_search_corrects_typos_before_ranking(monkeypatch, db_session):
    client = _FakeTmdbClient()
    monkeypatch.setattr(discover_details._search, "get_external_client", lambda: client)

    async def fake_tmdb_key(_db):
        return "test-key"

    monkeypatch.setattr(discover_details._search, "_get_tmdb_key", fake_tmdb_key)

    items = await discover_details.search_tmdb_multi(
        db_session,
        "enquet criminellle",
    )

    assert "enquetes criminelles" in client.queries
    assert [item["tmdb_id"] for item in items] == [20, 10]


@pytest.mark.asyncio
async def test_search_corrects_gender_suffix_before_ranking(monkeypatch, db_session):
    client = _FakeTmdbClient()
    monkeypatch.setattr(discover_details._search, "get_external_client", lambda: client)

    async def fake_tmdb_key(_db):
        return "test-key"

    monkeypatch.setattr(discover_details._search, "_get_tmdb_key", fake_tmdb_key)

    items = await discover_details.search_tmdb_multi(
        db_session,
        "enquete criminel",
    )

    assert "enquetes criminelles" in client.queries
    assert [item["tmdb_id"] for item in items] == [20, 10]


@pytest.mark.asyncio
async def test_search_splits_missing_hyphen_before_ranking(monkeypatch, db_session):
    client = _FakeTmdbClient()
    monkeypatch.setattr(discover_details._search, "get_external_client", lambda: client)

    async def fake_tmdb_key(_db):
        return "test-key"

    monkeypatch.setattr(discover_details._search, "_get_tmdb_key", fake_tmdb_key)

    items = await discover_details.search_tmdb_multi(db_session, "ironknight")

    assert "iron knight" in client.queries
    assert [item["tmdb_id"] for item in items] == [70, 80]


@pytest.mark.asyncio
async def test_search_splits_missing_word_separator_before_ranking(monkeypatch, db_session):
    client = _FakeTmdbClient()
    monkeypatch.setattr(discover_details._search, "get_external_client", lambda: client)

    async def fake_tmdb_key(_db):
        return "test-key"

    monkeypatch.setattr(discover_details._search, "_get_tmdb_key", fake_tmdb_key)

    items = await discover_details.search_tmdb_multi(db_session, "ghostmission")

    assert "ghost mission" in client.queries
    assert [item["tmdb_id"] for item in items] == [71, 81]


@pytest.mark.asyncio
async def test_search_splits_missing_plural_separator_before_ranking(monkeypatch, db_session):
    client = _FakeTmdbClient()
    monkeypatch.setattr(discover_details._search, "get_external_client", lambda: client)

    async def fake_tmdb_key(_db):
        return "test-key"

    monkeypatch.setattr(discover_details._search, "_get_tmdb_key", fake_tmdb_key)

    items = await discover_details.search_tmdb_multi(db_session, "enquetescriminelles")

    assert "enquetes criminelles" in client.queries
    assert [item["tmdb_id"] for item in items] == [20, 10]


@pytest.mark.asyncio
async def test_search_corrects_english_typo_and_uses_profile_language(monkeypatch, db_session):
    client = _FakeTmdbClient()
    monkeypatch.setattr(discover_details._search, "get_external_client", lambda: client)

    async def fake_tmdb_key(_db):
        return "test-key"

    monkeypatch.setattr(discover_details._search, "_get_tmdb_key", fake_tmdb_key)

    items = await discover_details.search_tmdb_multi(
        db_session,
        "criminal investigattion",
        language="en",
    )

    assert client.languages[0] == "en-US"
    assert "criminal investigation" in client.queries
    assert [item["tmdb_id"] for item in items] == [40, 30]
