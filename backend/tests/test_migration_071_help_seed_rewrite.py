"""Migration 071: six starter help articles rewritten where the admin left them as is.

Bootstraps a fresh SQLite DB from the current metadata, stamps it at 070, seeds
articles with the original text, an edited one and a trashed one, then runs the
071 upgrade. Also checks the rewrite is the current starter text.
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
REVISION = "071_help_seed_rewrite"
PREVIOUS = "070_profile_onboarding"
_SPEC = importlib.util.spec_from_file_location(
    "migration_071", BACKEND_ROOT / "alembic" / "versions" / "071_help_seed_rewrite.py",
)
migration = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(migration)


@pytest.fixture
def alembic_db(workspace_tmp_path, monkeypatch):
    backend_str = str(BACKEND_ROOT)
    added = backend_str not in sys.path
    if added:
        sys.path.insert(0, backend_str)
    db_path = Path(workspace_tmp_path) / "alembic_071.sqlite"
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


def _add_article(
    conn, article_id: int, slug: str, body: str, *, trashed: bool = False, title: str | None = None,
) -> None:
    articles = Base.metadata.tables["help_articles"]
    translations = Base.metadata.tables["help_article_translations"]
    conn.execute(sa.insert(articles).values(
        id=article_id, slug=slug, category="requests", sort_order=0, is_draft=False,
        deleted_at=datetime(2026, 11, 1, tzinfo=UTC) if trashed else None,
    ))
    conn.execute(sa.insert(translations).values(
        article_id=article_id, lang="fr", title=title or migration.TITLES.get(slug, slug),
        body_html=body,
    ))


def _bodies(engine) -> dict[int, str]:
    translations = Base.metadata.tables["help_article_translations"]
    with engine.connect() as conn:
        return dict(conn.execute(
            sa.select(translations.c.article_id, translations.c.body_html)
        ).all())


def test_rewrites_only_the_articles_left_as_seeded(alembic_db):
    cfg, engine = alembic_db
    request_old, request_new = migration.REWRITES["comment-faire-une-demande"]
    with engine.begin() as conn:
        _add_article(conn, 1, "comment-faire-une-demande", sanitize_html(request_old.strip()))
        _add_article(conn, 2, "choisir-son-pseudo", "<p>Our own house rules.</p>")
        _add_article(conn, 3, "les-differents-tags", sanitize_html(request_old.strip()))

    command.upgrade(cfg, REVISION)

    bodies = _bodies(engine)
    assert bodies[1] == sanitize_html(request_new.strip())
    assert bodies[2] == "<p>Our own house rules.</p>"  # rewritten by the admin: kept
    assert bodies[3] == sanitize_html(request_old.strip())  # not one of the six articles


def test_each_of_the_six_articles_is_rewritten(alembic_db):
    cfg, engine = alembic_db
    slugs = sorted(migration.REWRITES)
    with engine.begin() as conn:
        for article_id, slug in enumerate(slugs, start=1):
            _add_article(conn, article_id, slug, sanitize_html(migration.REWRITES[slug][0].strip()))

    command.upgrade(cfg, REVISION)

    bodies = _bodies(engine)
    for article_id, slug in enumerate(slugs, start=1):
        assert bodies[article_id] == sanitize_html(migration.REWRITES[slug][1].strip()), slug


def test_leaves_a_trashed_article_alone(alembic_db):
    cfg, engine = alembic_db
    request_old, _ = migration.REWRITES["comment-faire-une-demande"]
    with engine.begin() as conn:
        _add_article(conn, 1, "comment-faire-une-demande", sanitize_html(request_old.strip()), trashed=True)

    command.upgrade(cfg, REVISION)

    assert _bodies(engine)[1] == sanitize_html(request_old.strip())


def test_matches_the_original_text_whatever_its_spacing():
    request_old, _ = migration.REWRITES["comment-faire-une-demande"]
    # As a sanitizer may store it: other spacing, an entity for the quote mark.
    squeezed = " ".join(request_old.split()).replace(chr(0xAB), "&laquo;")
    assert migration.shape(squeezed) == migration.shape(request_old)


@pytest.mark.parametrize("retouch", ["picture", "title"])
def test_leaves_an_article_the_admin_retouched_alone(alembic_db, retouch):
    cfg, engine = alembic_db
    request_old, _ = migration.REWRITES["comment-faire-une-demande"]
    body = sanitize_html(request_old.strip())
    title = None
    if retouch == "picture":  # same words, one more picture
        body += '<p><img src="https://example.com/a.png" alt=""></p>'
    else:
        title = "Faire une demande, pas à pas"
    with engine.begin() as conn:
        _add_article(conn, 1, "comment-faire-une-demande", body, title=title)

    command.upgrade(cfg, REVISION)

    assert _bodies(engine)[1] == body


@pytest.mark.parametrize("slug", sorted(migration.REWRITES))
def test_the_rewrite_is_the_current_starter_text(slug):
    seeded = next(entry for entry in HELP_SEED if entry["slug"] == slug)
    assert migration.REWRITES[slug][1].strip() == seeded["fr"]["body_html"]
