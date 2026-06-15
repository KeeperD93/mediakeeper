"""Reset a backoffice admin account password from the host shell.

Self-hosted operators routinely lose the initial admin password that
``_emit_bootstrap_admin_credentials`` prints on first boot — it never
hits the volume and is gone the moment the container's log buffer
rotates. This script is the supported recovery path: it generates a
fresh random password, writes it to ``stdout`` only (never logged,
never persisted), forces ``must_change_password=True`` so the next
login still requires picking a real password, and stamps
``tokens_invalidated_at`` to revoke every JWT issued under the old
credentials.

Usage (from the host running the container):

    docker exec -w /app/backend mediakeeper \
        python -m scripts.reset_admin --username admin

Exit codes:
* ``0`` — password reset successfully (the new password is printed on
  stdout, separated by a banner that operators can copy verbatim).
* ``1`` — the user does not exist.
* ``2`` — refused: the named user exists but is not flagged as a
  backoffice admin (avoids reset-by-mistake on a portal-only account).
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import secrets
import sys
from datetime import datetime, timezone

from sqlalchemy import select

from core.database import AsyncSessionLocal
from core.security import hash_password, is_backoffice_admin
from models.user import User

logger = logging.getLogger("mediakeeper.scripts.reset_admin")


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m scripts.reset_admin",
        description=(
            "Reset a backoffice admin account password. Prints the new "
            "credentials on stdout — capture them immediately, they are "
            "never persisted."
        ),
    )
    parser.add_argument(
        "--username",
        default="admin",
        help="Target username (default: admin)",
    )
    return parser


def _emit_credentials(username: str, password: str) -> None:
    banner = "=" * 60
    sys.stdout.write(
        f"{banner}\n"
        f"  ADMIN PASSWORD RESET\n"
        f"  Username: {username}\n"
        f"  Password: {password}\n"
        f"  You MUST change this password on next login.\n"
        f"  Existing sessions have been invalidated.\n"
        f"{banner}\n"
    )
    sys.stdout.flush()


async def _reset(username: str, *, session_factory=None) -> int:
    factory = session_factory or AsyncSessionLocal
    async with factory() as session:
        result = await session.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()
        if user is None:
            sys.stderr.write(f"user not found: {username!r}\n")
            return 1
        if not is_backoffice_admin(user.username):
            sys.stderr.write(
                f"refused: {username!r} is not a backoffice admin. Use the "
                f"portal admin tools to manage non-admin accounts.\n"
            )
            return 2

        new_password = secrets.token_urlsafe(32)
        user.hashed_password = hash_password(new_password)
        user.must_change_password = True
        user.tokens_invalidated_at = datetime.now(timezone.utc)
        await session.commit()

    _emit_credentials(username, new_password)
    logger.info("[reset_admin] Password reset for user_id=%s", user.id)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _build_arg_parser().parse_args(argv)
    return asyncio.run(_reset(args.username))


if __name__ == "__main__":
    raise SystemExit(main())
