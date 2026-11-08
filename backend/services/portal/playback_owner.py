"""Which rows of the playback tables belong to a player."""
from sqlalchemy import and_, or_, select

from models.portal.profile import UserProfile


def played_by(model, emby_user_id: str | None, login: str | None):
    """WHERE clause for a player's rows of ``model`` (sessions, pause events), ``None`` for nobody.

    Never by pseudo, which anyone can choose. The Emby id decides; the login only claims
    the rows of an Emby account linked to no profile, as after Emby is reinstalled.
    """
    clauses = []
    if emby_user_id:
        clauses.append(model.user_id == emby_user_id)
    if login:
        linked = select(UserProfile.emby_user_id).where(UserProfile.emby_user_id.is_not(None))
        clauses.append(and_(model.user_name == login, model.user_id.not_in(linked)))
    return or_(*clauses) if clauses else None
