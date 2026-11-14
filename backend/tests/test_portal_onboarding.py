"""First-login wizard: the choices saved at once at the end, the display name
judged by the save's own rules, a second submit saving nothing, and the profile
telling the portal whether the wizard is still to do."""
from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from sqlalchemy import text

from services.portal import daily_digest as dd_svc
from services.portal import onboarding as onboarding_svc
from services.portal.gdpr import _collect_full_user_data
from tests._portal_profile_helpers import PORTAL_COOKIE, make_portal_user, portal_token

URL = "/api/portal/profiles/me/onboarding"
ME_URL = "/api/portal/profiles/me"


async def _login(client, db_session, **kwargs):
    user, profile = await make_portal_user(db_session, **kwargs)
    client.cookies.set(PORTAL_COOKIE, portal_token(user.username))
    return user, profile


def _choices(**extra) -> dict:
    return {
        "display_name": "Cinephile42",
        "language": "en",
        "is_public": False,
        "favorite_genres": [28, 35],
        **extra,
    }


@pytest.mark.asyncio
async def test_profile_says_the_wizard_is_to_do_until_finished(client, db_session):
    await _login(client, db_session, username="alice", must_set=True)
    assert (await client.get(ME_URL)).json()["onboarding_pending"] is True

    resp = await client.post(URL, json=_choices())
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["onboarding_pending"] is False
    assert (await client.get(ME_URL)).json()["onboarding_pending"] is False


@pytest.mark.asyncio
async def test_finishing_saves_every_choice_at_once(client, db_session):
    await _login(client, db_session, username="alice", must_set=True)
    body = (await client.post(URL, json=_choices())).json()
    assert body["display_name"] == "Cinephile42"
    assert body["display_name_must_set"] is False
    assert body["display_name_changed_at"] is not None
    assert body["language"] == "en"
    assert body["is_public"] is False
    assert body["favorite_genres"] == [28, 35]


@pytest.mark.asyncio
async def test_default_language_is_kept_as_inherited(client, db_session):
    await _login(client, db_session, username="alice", must_set=True)
    body = (await client.post(URL, json=_choices(language=None))).json()
    assert body["language"] is None


@pytest.mark.asyncio
async def test_a_refused_name_saves_nothing(client, db_session):
    await make_portal_user(db_session, username="bob", display_name="Taken")
    await _login(client, db_session, username="alice", must_set=True)

    resp = await client.post(URL, json=_choices(display_name="taken"))
    assert resp.status_code == 409
    assert resp.json()["detail"] == "display_name_taken"
    me = (await client.get(ME_URL)).json()
    assert me["onboarding_pending"] is True
    assert me["language"] is None
    assert me["is_public"] is True


@pytest.mark.asyncio
async def test_existing_member_keeps_their_name_without_a_new_lock(client, db_session):
    await _login(
        client, db_session, username="alice", display_name="Alice", changed_days_ago=400,
    )
    body = (await client.post(URL, json=_choices(display_name="alice"))).json()
    assert body["display_name"] == "Alice"
    # Changed 400 days ago: its lock ended long ago; a fresh stamp would push it ahead.
    assert datetime.fromisoformat(body["display_name_locked_until"]) < datetime.now(UTC)
    assert body["onboarding_pending"] is False


@pytest.mark.asyncio
async def test_a_second_submit_saves_nothing(client, db_session):
    await _login(client, db_session, username="alice", must_set=True)
    first = (await client.post(URL, json=_choices())).json()

    resp = await client.post(URL, json=_choices(display_name="Another", is_public=True))
    assert resp.status_code == 200
    body = resp.json()
    assert body["display_name"] == first["display_name"]
    assert body["is_public"] is False


@pytest.mark.asyncio
async def test_forced_public_profile_cannot_go_private(client, db_session):
    _, profile = await _login(client, db_session, username="alice", must_set=True)
    profile.forced_public = True
    await db_session.commit()

    resp = await client.post(URL, json=_choices(is_public=False))
    assert resp.status_code == 403
    assert resp.json()["detail"] == "profile_visibility_locked"
    assert (await client.get(ME_URL)).json()["onboarding_pending"] is True


@pytest.mark.asyncio
async def test_admin_finishes_with_a_reserved_name_of_their_own(client, db_session):
    await _login(client, db_session, username="admin", display_name="admin", role="admin")
    resp = await client.post(URL, json=_choices(display_name="admin"))
    assert resp.status_code == 200, resp.text
    assert resp.json()["onboarding_pending"] is False


@pytest.mark.asyncio
@pytest.mark.parametrize("extra", [
    {"language": "de"},
    {"favorite_genres": [0]},
    {"favorite_genres": list(range(1, 32))},
    {"bio": "hello"},
])
async def test_choices_outside_the_wizard_are_refused(client, db_session, extra):
    await _login(client, db_session, username="alice", must_set=True)
    resp = await client.post(URL, json=_choices(**extra))
    assert resp.status_code == 422


def _watch_digest_cache(monkeypatch) -> dict[str, list]:
    calls: dict[str, list] = {"cleared": [], "dropped": []}
    monkeypatch.setattr(dd_svc, "clear_cache", lambda: calls["cleared"].append(True))
    monkeypatch.setattr(dd_svc, "invalidate_cache", calls["dropped"].append)
    return calls


@pytest.mark.asyncio
async def test_finishing_rebuilds_every_digest(client, db_session, monkeypatch):
    # The member's greets the new name; the others' podiums show it, or drop a private profile.
    await _login(client, db_session, username="alice", must_set=True)
    calls = _watch_digest_cache(monkeypatch)

    await client.post(URL, json=_choices())
    assert calls == {"cleared": [True], "dropped": []}

    await client.post(URL, json=_choices())  # already finished: nothing saved, nothing rebuilt
    assert calls == {"cleared": [True], "dropped": []}


@pytest.mark.asyncio
@pytest.mark.parametrize(("change", "seen_by_others"), [
    ({"is_public": False}, True),
    ({"display_name": "Alicia"}, True),
    ({"bio": "Hello"}, False),
    ({"is_public": True}, False),  # unchanged: only the member's own digest goes
    ({"display_name": "alice"}, False),  # the same name: kept as it is
])
async def test_a_profile_save_rebuilds_the_digests_it_touches(
    client, db_session, monkeypatch, change, seen_by_others,
):
    user, _ = await _login(client, db_session, username="alice", display_name="Alice")
    calls = _watch_digest_cache(monkeypatch)

    resp = await client.put(ME_URL, json=change)
    assert resp.status_code == 200, resp.text
    if seen_by_others:
        assert calls == {"cleared": [True], "dropped": []}
    else:
        assert calls == {"cleared": [], "dropped": [user.id]}


@pytest.mark.asyncio
@pytest.mark.parametrize("name", ["   ", "<b></b>", chr(0xFEFF) * 3])
async def test_a_name_that_cleans_down_to_nothing_ends_nothing(client, db_session, name):
    await _login(client, db_session, username="alice", must_set=True)
    resp = await client.post(URL, json=_choices(display_name=name))
    assert resp.status_code == 422
    assert resp.json()["detail"] == "display_name_invalid"
    assert (await client.get(ME_URL)).json()["onboarding_pending"] is True


@pytest.mark.asyncio
@pytest.mark.parametrize("stored", ["Admin Bob", "Root66", "Ali" + chr(0x200D) + "ce"])
async def test_a_refused_stored_name_can_be_changed_despite_the_lock(client, db_session, stored):
    # Changed a month ago under older rules, or by an admin: neither kept nor locked.
    await _login(client, db_session, username="bob", display_name=stored, changed_days_ago=30)
    state = (await client.get("/api/portal/profiles/me/username-state")).json()
    assert state["locked"] is False

    resp = await client.post(URL, json=_choices(display_name="Robert"))
    assert resp.status_code == 200, resp.text
    assert resp.json()["display_name"] == "Robert"


@pytest.mark.asyncio
async def test_an_accepted_name_stays_locked(client, db_session):
    await _login(client, db_session, username="bob", display_name="Bobby", changed_days_ago=30)
    resp = await client.post(URL, json=_choices(display_name="Robert"))
    assert resp.status_code == 403
    assert resp.json()["detail"] == "display_name_locked"


@pytest.mark.asyncio
async def test_choices_left_out_keep_their_stored_value(client, db_session):
    _, profile = await _login(client, db_session, username="carol", display_name="Carol")
    profile.language = "en"
    profile.favorite_genres = [28, 35]
    await db_session.commit()

    resp = await client.post(URL, json={"display_name": "Carol", "is_public": True})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert (body["language"], body["favorite_genres"]) == ("en", [28, 35])


@pytest.mark.asyncio
async def test_the_data_export_carries_the_finish_date(client, db_session):
    user, profile = await _login(client, db_session, username="alice", must_set=True)
    assert (await client.post(URL, json=_choices())).status_code == 200
    await db_session.refresh(profile)
    exported = (await _collect_full_user_data(db_session, user, profile))["user_profile"]
    assert exported["onboarding_completed_at"] is not None


@pytest.mark.asyncio
async def test_a_stale_session_sees_the_wizard_finished_elsewhere(db_session):
    user, profile = await make_portal_user(db_session, username="alice", must_set=True)
    # Another request finished the wizard: the row changes, this session's object does not.
    await db_session.execute(
        text(
            "UPDATE user_profiles SET onboarding_completed_at = :at, display_name = 'Winner'"
            " WHERE user_id = :u"
        ),
        {"at": datetime.now(UTC), "u": user.id},
    )
    await db_session.commit()
    assert profile.onboarding_completed_at is None  # stale on purpose

    result = await onboarding_svc.complete_onboarding(db_session, user.id, _choices())
    assert result.display_name == "Winner"
    assert result.display_name_must_set is True  # the second finish wrote nothing


@pytest.mark.asyncio
async def test_the_profile_is_locked_on_postgresql(db_session, monkeypatch):
    user, _ = await make_portal_user(db_session, username="alice", must_set=True)
    seen = []
    real_execute = db_session.execute

    async def recording_execute(stmt, *args, **kwargs):
        seen.append(stmt)
        return await real_execute(stmt, *args, **kwargs)

    monkeypatch.setattr(db_session, "execute", recording_execute)
    # White box: the dialect is reported as PostgreSQL, the statement is read back.
    monkeypatch.setattr(
        db_session, "get_bind",
        lambda *a, **k: SimpleNamespace(dialect=SimpleNamespace(name="postgresql")),
    )
    await onboarding_svc.complete_onboarding(db_session, user.id, _choices())
    first = seen[0]
    assert getattr(first, "_for_update_arg", None) is not None
    assert first.get_execution_options().get("populate_existing") is True
