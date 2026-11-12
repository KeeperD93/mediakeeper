"""What an admin decides on before a watch XP recalculation, and the print of the plan
behind it: apply refuses a plan the admin has not seen."""
import hashlib
from dataclasses import replace

from services.portal.xp import boosted_watch_xp
from services.portal.xp_boost import event_applies, multiplier_at

from ._context import BonusEvent, Context
from ._months import MonthChanges
from ._plan import Plan


def fingerprint(ctx: Context, plan: Plan) -> str:
    """The rows due up to ``as_of`` (reference, XP, date) and the accounts of the scope.
    Neither the ledger nor the profiles: a title watched before ``as_of`` and paid an
    instant later leaves it as it is."""
    digest = hashlib.sha256(",".join(str(user_id) for user_id in sorted(ctx.scope)).encode())
    for t in plan.targets:
        if t.at <= ctx.as_of:
            digest.update(f"|{t.user_id}:{t.reference}:{t.xp}:{t.at.isoformat()}".encode())
    return digest.hexdigest()[:16]


def _event(ctx: Context, ev: BonusEvent, plan: Plan) -> dict:
    """The titles an event covers, and the XP it adds to them (``enabled``) or would add."""
    others = [other for other in ctx.events if other.id != ev.id]
    with_it = [*others, replace(ev, enabled=True)]
    covered = [t for t in plan.targets if event_applies(ev, t.action, t.at)]
    bonus = sum(
        boosted_watch_xp(t.runtime, multiplier_at(with_it, t.action, t.at))
        - boosted_watch_xp(t.runtime, multiplier_at(others, t.action, t.at))
        for t in covered
    )
    return {
        "name": ev.name,
        "starts_at": ev.starts_at.isoformat(),
        "ends_at": ev.ends_at.isoformat(),
        "enabled": ev.enabled,
        "titles": len(covered),
        "bonus_xp": bonus,
    }


def summarize(ctx: Context, plan: Plan, months: MonthChanges, names: dict[int, str]) -> dict:
    changed = [player for player in plan.players if player.changed]
    level_moves = [player.level_after - player.level for player in changed]
    return {
        "as_of": ctx.as_of.isoformat(),
        "plan": fingerprint(ctx, plan),
        "players": len(plan.players),
        "players_changed": len(changed),
        "watch_xp_before": sum(row.xp for player in plan.players for row in (*player.kept, *player.deleted)),
        "watch_xp_after": sum(
            sum(row.xp for row in player.kept) + sum(t.xp for t in player.inserted) for player in plan.players
        ),
        "rows_deleted": sum(len(player.deleted) for player in changed),
        "rows_inserted": sum(len(player.inserted) for player in changed),
        "levels_up": sum(move > 0 for move in level_moves),
        "levels_down": sum(move < 0 for move in level_moves),
        "max_level_loss": max((-move for move in level_moves if move < 0), default=0),
        "lost": plan.lost,
        "skipped": plan.skipped,
        "namesakes": plan.namesakes,
        "events": [_event(ctx, ev, plan) for ev in ctx.events],
        "leaders_changed": list(months.leaders_changed),
        "competitor_new": months.competitor_new,
        "competitor_unjustified": months.competitor_unjustified,
        "rows": [
            {
                "user_id": player.user_id,
                "name": names.get(player.user_id),
                "xp": player.xp,
                "xp_after": player.xp_after,
                "level": player.level,
                "level_after": player.level_after,
                "deleted": len(player.deleted),
                "inserted": len(player.inserted),
            }
            for player in changed
        ],
    }
