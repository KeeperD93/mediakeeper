"""Migration 074: the XP and levels starter articles rewritten, French and English,
where the admin left them as is.

Bootstraps a fresh SQLite DB from the current metadata, stamps it at 073, seeds
articles with the starter text, edited ones and a trashed one, then runs the 074
upgrade. Also checks the rewrite is the current starter text and that it starts
from the text 071 wrote.
"""
from __future__ import annotations

import importlib.util
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config

from models.base import Base
from services.portal.help_content import HELP_SEED
from services.portal.help_sanitize import sanitize_html

BACKEND_ROOT = Path(__file__).resolve().parents[1]
VERSIONS = BACKEND_ROOT / "alembic" / "versions"
REVISION = "074_help_xp_levels_rewrite"
PREVIOUS = "073_completion_exclusive_seconds"
XP = "comment-gagner-de-l-xp"
LEVELS = "les-paliers-et-grades"


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, VERSIONS / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


migration = _load("migration_074", "074_help_xp_levels_rewrite.py")


@pytest.fixture
def alembic_db(workspace_tmp_path, monkeypatch):
    backend_str = str(BACKEND_ROOT)
    added = backend_str not in sys.path
    if added:
        sys.path.insert(0, backend_str)
    db_path = Path(workspace_tmp_path) / "alembic_074.sqlite"
    sync_url = f"sqlite:///{db_path.as_posix()}"
    engine = sa.create_engine(sync_url, future=True)
    Base.metadata.create_all(engine)
    monkeypatch.setenv("DATABASE_URL", sync_url)
    cfg = Config(str(BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    command.stamp(cfg, PREVIOUS)
    try:
        yield cfg, engine
    finally:
        engine.dispose()
        if added:
            sys.path.remove(backend_str)


def _starter(slug: str, lang: str, which: int = 0) -> str:
    return sanitize_html(migration.REWRITES[slug][lang][which].strip())


def _add_article(
    conn, article_id: int, slug: str, fr: str, en: str | None = None, *,
    trashed: bool = False, fr_title: str | None = None, en_title: str | None = None,
) -> None:
    articles = Base.metadata.tables["help_articles"]
    translations = Base.metadata.tables["help_article_translations"]
    conn.execute(sa.insert(articles).values(
        id=article_id, slug=slug, category="profile", sort_order=0, is_draft=False,
        deleted_at=datetime(2026, 11, 1, tzinfo=UTC) if trashed else None,
    ))
    conn.execute(sa.insert(translations).values(
        article_id=article_id, lang="fr", title=fr_title or migration.TITLES[slug]["fr"], body_html=fr,
    ))
    if en is not None:
        conn.execute(sa.insert(translations).values(
            article_id=article_id, lang="en", title=en_title or migration.TITLES[slug]["en"], body_html=en,
        ))


def _bodies(engine) -> dict[tuple[int, str], str]:
    translations = Base.metadata.tables["help_article_translations"]
    with engine.connect() as conn:
        rows = conn.execute(sa.select(
            translations.c.article_id, translations.c.lang, translations.c.body_html,
        )).all()
    return {(article_id, lang): body for article_id, lang, body in rows}


def test_rewrites_both_articles_in_both_languages(alembic_db):
    cfg, engine = alembic_db
    with engine.begin() as conn:
        _add_article(conn, 1, XP, _starter(XP, "fr"), _starter(XP, "en"))
        _add_article(conn, 2, LEVELS, _starter(LEVELS, "fr"), _starter(LEVELS, "en"))

    command.upgrade(cfg, REVISION)

    bodies = _bodies(engine)
    for article_id, slug in ((1, XP), (2, LEVELS)):
        assert bodies[(article_id, "fr")] == _starter(slug, "fr", 1), slug
        assert bodies[(article_id, "en")] == _starter(slug, "en", 1), slug


def test_rewrites_the_french_of_an_article_without_english(alembic_db):
    cfg, engine = alembic_db
    with engine.begin() as conn:
        _add_article(conn, 1, LEVELS, _starter(LEVELS, "fr"))

    command.upgrade(cfg, REVISION)

    assert _bodies(engine) == {(1, "fr"): _starter(LEVELS, "fr", 1)}


@pytest.mark.parametrize("retouch", ["picture", "word", "title"])
def test_leaves_an_article_whose_french_the_admin_retouched_alone(alembic_db, retouch):
    cfg, engine = alembic_db
    fr = _starter(XP, "fr")
    fr_title = None
    if retouch == "picture":  # same words, one more picture
        fr += '<p><img src="https://example.com/a.png" alt=""></p>'
    elif retouch == "word":  # one word more, nothing else
        fr = fr.replace("</p>", " vraiment</p>", 1)
    else:
        fr_title = "Gagner de l'XP, pas à pas"
    with engine.begin() as conn:
        _add_article(conn, 1, XP, fr, _starter(XP, "en"), fr_title=fr_title)

    command.upgrade(cfg, REVISION)

    bodies = _bodies(engine)
    assert bodies[(1, "fr")] == fr
    assert bodies[(1, "en")] == _starter(XP, "en")  # follows its French: kept


@pytest.mark.parametrize("retouch", ["word", "title"])
def test_keeps_an_english_text_the_admin_retouched(alembic_db, retouch):
    cfg, engine = alembic_db
    en = _starter(LEVELS, "en")
    en_title = None
    if retouch == "word":
        en = en.replace("</p>", " indeed</p>", 1)
    else:
        en_title = "Our ranks"
    with engine.begin() as conn:
        _add_article(conn, 1, LEVELS, _starter(LEVELS, "fr"), en, en_title=en_title)

    command.upgrade(cfg, REVISION)

    bodies = _bodies(engine)
    assert bodies[(1, "fr")] == _starter(LEVELS, "fr", 1)
    assert bodies[(1, "en")] == en


def test_leaves_a_trashed_article_alone(alembic_db):
    cfg, engine = alembic_db
    with engine.begin() as conn:
        _add_article(conn, 1, XP, _starter(XP, "fr"), _starter(XP, "en"), trashed=True)

    command.upgrade(cfg, REVISION)

    assert _bodies(engine) == {(1, "fr"): _starter(XP, "fr"), (1, "en"): _starter(XP, "en")}


def test_rewrites_an_untouched_article_whose_slug_moved(alembic_db):
    # An older editor save moved the slug without touching a word.
    cfg, engine = alembic_db
    with engine.begin() as conn:
        _add_article(conn, 1, "paliers-et-grades", _starter(LEVELS, "fr"), _starter(LEVELS, "en"),
                     fr_title=migration.TITLES[LEVELS]["fr"], en_title=migration.TITLES[LEVELS]["en"])

    command.upgrade(cfg, REVISION)

    bodies = _bodies(engine)
    assert bodies[(1, "fr")] == _starter(LEVELS, "fr", 1)
    assert bodies[(1, "en")] == _starter(LEVELS, "en", 1)


def test_leaves_other_articles_alone(alembic_db):
    cfg, engine = alembic_db
    with engine.begin() as conn:
        _add_article(conn, 1, "le-classement-mensuel", _starter(XP, "fr"), fr_title="Le classement mensuel")

    command.upgrade(cfg, REVISION)

    assert _bodies(engine) == {(1, "fr"): _starter(XP, "fr")}


@pytest.mark.parametrize("slug", [XP, LEVELS])
@pytest.mark.parametrize("lang", ["fr", "en"])
def test_the_rewrite_is_the_current_starter_text(slug, lang):
    seeded = next(entry for entry in HELP_SEED if entry["slug"] == slug)
    assert migration.REWRITES[slug][lang][1].strip() == seeded[lang]["body_html"]
    assert migration.TITLES[slug][lang] == seeded[lang]["title"]


def test_the_xp_article_starts_from_the_text_071_wrote():
    rewrite_071 = _load("migration_071", "071_help_seed_rewrite.py").REWRITES[XP][1]
    assert migration.REWRITES[XP]["fr"][0].strip() == rewrite_071.strip()
