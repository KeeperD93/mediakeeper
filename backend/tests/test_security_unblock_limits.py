"""What an unblock leaves alone: an admin's blocks, other scopes, other incidents,
and a failure that arrives while it runs."""
import pytest
from sqlalchemy import delete, select

from models.security import SecurityBlock
from services.security import FAIL_BLOCK_THRESHOLD, _auto_block, release_block
from tests._security_unblock_helpers import (
    AWAY,
    HOME,
    OTHER,
    add_attempt,
    add_block,
    fail,
    find_block,
    remaining_blocks,
    still_counting,
)


@pytest.mark.asyncio
async def test_a_manual_block_on_the_same_name_or_address_stays(db_session):
    """Its creator deleted, it has no created_by left: the marker keeps it an admin's."""
    await fail(db_session, HOME, "member-a")
    await add_block(db_session, username="member-a", automatic=0, ends_in=7200)
    await add_block(db_session, ip=HOME, automatic=0, ends_in=7200)
    automatic_name = (await db_session.execute(
        select(SecurityBlock.id).where(SecurityBlock.username == "member-a", SecurityBlock.automatic == 1)
    )).scalar_one()

    released = await release_block(db_session, automatic_name)

    assert released["linked_addresses"] == 1
    assert await remaining_blocks(db_session) == {(None, "member-a", "portal"), (HOME, None, "portal")}
    assert (await db_session.execute(
        select(SecurityBlock.automatic).distinct()
    )).scalars().all() == [0]


@pytest.mark.asyncio
async def test_lifting_a_manual_block_touches_nothing_else(db_session):
    await fail(db_session, HOME, "member-a")
    manual = await add_block(db_session, username="member-a", automatic=0)

    released = await release_block(db_session, manual)

    assert [r["id"] for r in released["removed"]] == [manual]
    assert released["linked_addresses"] == 0
    assert await remaining_blocks(db_session) == {(None, "member-a", "portal"), (HOME, None, "portal")}
    assert len(await still_counting(db_session)) == FAIL_BLOCK_THRESHOLD


@pytest.mark.asyncio
async def test_other_scopes_keep_their_blocks_and_failures(db_session):
    await fail(db_session, HOME, "member-a", scope="admin")
    await fail(db_session, HOME, "member-a", scope="portal")

    await release_block(db_session, await find_block(db_session, username="member-a", scope="portal"))

    assert await remaining_blocks(db_session) == {(None, "member-a", "admin"), (HOME, None, "admin")}
    assert len(await still_counting(db_session)) == FAIL_BLOCK_THRESHOLD


@pytest.mark.asyncio
async def test_a_late_unblock_still_frees_the_address(db_session):
    """Past the 5-minute count but within its 10-minute block, the address is still linked."""
    await add_attempt(db_session, HOME, "member-a", age=420)
    name_id = await add_block(db_session, username="member-a", ends_in=180)
    await add_block(db_session, ip=HOME, ends_in=180)

    released = await release_block(db_session, name_id)

    assert released["linked_addresses"] == 1
    assert await still_counting(db_session) == []


@pytest.mark.asyncio
async def test_an_old_failure_links_no_address_and_stays_as_it_is(db_session):
    """Older than any block still in force: another incident's address stays blocked."""
    await add_attempt(db_session, OTHER, "member-a", age=1000)
    name_id = await add_block(db_session, username="member-a")
    await add_block(db_session, ip=OTHER)

    released = await release_block(db_session, name_id)

    assert released["linked_addresses"] == 0
    assert await remaining_blocks(db_session) == {(OTHER, None, "portal")}
    assert await still_counting(db_session) == [(OTHER, "member-a")]


@pytest.mark.asyncio
async def test_an_expired_block_is_not_reported_as_freed(db_session):
    await add_attempt(db_session, HOME, "member-a")
    name_id = await add_block(db_session, username="member-a")
    await add_block(db_session, ip=HOME, ends_in=-60)

    released = await release_block(db_session, name_id)

    assert released["linked_addresses"] == 0
    assert await remaining_blocks(db_session) == {(HOME, None, "portal")}


@pytest.mark.asyncio
async def test_a_block_that_just_expired_can_still_be_lifted(db_session):
    expired = await add_block(db_session, username="member-a", ends_in=-1)

    released = await release_block(db_session, expired)

    assert [r["id"] for r in released["removed"]] == [expired]
    assert await remaining_blocks(db_session) == set()


@pytest.mark.asyncio
async def test_an_address_found_through_a_neutralised_failure_is_still_freed(db_session):
    """An earlier unblock cleared the failure, not the fact that the name failed there."""
    await add_attempt(db_session, HOME, "member-a", cleared=True)
    name_id = await add_block(db_session, username="member-a")
    await add_block(db_session, ip=HOME)

    released = await release_block(db_session, name_id)

    assert released["linked_addresses"] == 1
    assert await remaining_blocks(db_session) == set()


@pytest.mark.asyncio
async def test_a_failure_arriving_during_the_unblock_still_counts(db_session):
    """Logged after the click, it was not behind the block that was lifted. A success never counted."""
    await add_attempt(db_session, HOME, "member-a", age=-30)
    await add_attempt(db_session, AWAY, "member-a", success=1)
    name_id = await add_block(db_session, username="member-a")

    await release_block(db_session, name_id)

    assert await still_counting(db_session) == [(HOME, "member-a"), (AWAY, "member-a")]


@pytest.mark.asyncio
async def test_a_block_stored_with_capitals_is_matched_with_its_name(db_session):
    await add_attempt(db_session, HOME, "member-a")
    name_id = await add_block(db_session, username="Member-A")
    await add_block(db_session, username="member-a")
    await add_block(db_session, ip=HOME)

    released = await release_block(db_session, name_id)

    assert released["linked_addresses"] == 1
    assert await remaining_blocks(db_session) == set()
    assert await still_counting(db_session) == []


@pytest.mark.asyncio
async def test_an_unknown_block_answers_none(db_session):
    assert await release_block(db_session, 12345) is None


@pytest.mark.asyncio
async def test_a_failure_racing_an_unblock_still_gets_its_answer(db_session, monkeypatch):
    """The block being renewed is lifted between its lookup and its renewal: that
    sign-in must not fail over a row already gone."""
    row_id = await add_block(db_session, username="member-a", ends_in=-60)
    real_execute = db_session.execute
    lifted = False

    async def _execute(statement, *args, **kwargs):
        nonlocal lifted
        result = await real_execute(statement, *args, **kwargs)
        if not lifted:
            lifted = True
            await real_execute(
                delete(SecurityBlock).where(SecurityBlock.id == row_id)
                .execution_options(synchronize_session=False)
            )
        return result

    monkeypatch.setattr(db_session, "execute", _execute)
    await _auto_block(db_session, ip=None, username="member-a", scope="portal", reason_suffix="username")

    monkeypatch.undo()
    assert await remaining_blocks(db_session) == set()
