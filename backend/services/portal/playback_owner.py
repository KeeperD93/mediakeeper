"""Which rows of the playback tables belong to a player."""
from sqlalchemy import and_, false, func, or_, select

from models.portal.profile import UserProfile


def played_by(model, emby_user_id: str | None, login: str | None):
    """WHERE clause for a player's rows of ``model`` (sessions, pause events), ``None`` for nobody.

    Never by pseudo, which anyone can choose. The Emby id decides, unless several profiles
    share it: then only the name tells them apart, as at sign-in. The login, compared without
    case (A to Z only, under the C locale of production), also claims the rows of an Emby
    account linked to no profile, as after Emby is reinstalled.
    """
    linked = select(UserProfile.emby_user_id).where(UserProfile.emby_user_id.is_not(None))
    named = func.lower(model.user_name) == func.lower(login) if login else false()
    clauses = []
    if emby_user_id:
        shared = linked.group_by(UserProfile.emby_user_id).having(func.count() > 1)
        clauses.append(and_(model.user_id == emby_user_id, or_(model.user_id.not_in(shared), named)))
    if login:
        clauses.append(and_(named, model.user_id.not_in(linked)))
    return or_(*clauses) if clauses else None
