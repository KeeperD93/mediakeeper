"""The totals an admin decides on, with no player named, and the print of the plan behind them."""
import hashlib
from collections import Counter

from ._context import Context
from ._plan import PlayerPlan


def fingerprint(ctx: Context, plans: list[PlayerPlan]) -> str:
    """Changes as soon as a single removal does: apply refuses a plan the admin has not seen."""
    digest = hashlib.sha256(f"{ctx.zone_name}|{ctx.zone_saved_at.isoformat()}".encode())
    for plan in sorted(plans, key=lambda p: p.user_id):
        if plan.removed:
            digest.update(f"|{plan.user_id}:{','.join(sorted(plan.removed))}".encode())
    return digest.hexdigest()[:16]


def _counted(ctx: Context, counts: Counter) -> list[dict]:
    return [
        {"achievement_id": a, "name_key": ctx.achievements[a].name_key, "count": n}
        for a, n in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    ]


def summarize(ctx: Context, plans: list[PlayerPlan], failed: int) -> dict:
    direct = Counter(a for plan in plans for a in plan.direct)
    from_cascade = Counter(a for plan in plans for a in plan.cascade)
    imported = Counter(a for plan in plans for a in plan.imported)
    affected = [plan for plan in plans if plan.removed]
    level_losses = [plan.level - plan.level_after for plan in affected if plan.level_after < plan.level]
    removals = [
        {
            "achievement_id": a,
            "name_key": ctx.achievements[a].name_key,
            "direct": direct[a],
            "cascade": from_cascade[a],
            "imported": imported[a],
        }
        for a in sorted(direct | from_cascade, key=lambda a: (-(direct[a] + from_cascade[a]), a))
    ]
    return {
        "timezone": ctx.zone_name,
        "zone_saved_at": ctx.zone_saved_at.isoformat(),
        "plan": fingerprint(ctx, plans),
        "players": len(plans),
        "players_affected": len(affected),
        "players_failed": failed,
        "removals": removals,
        "removed_total": sum(len(plan.removed) for plan in plans),
        "removed_imported": imported.total(),
        "xp_removed": sum(plan.xp - plan.xp_after for plan in affected),
        "players_losing_level": len(level_losses),
        "max_level_loss": max(level_losses, default=0),
        "decorations_removed": sum(len(plan.decorations) for plan in affected),
        "kept_nowhere": _counted(ctx, Counter(a for plan in plans for a in plan.kept_nowhere)),
        "kept_gifts": _counted(ctx, Counter(a for plan in plans for a in plan.kept_gifts)),
        "competitor_months": ctx.competitor_months,
        "king_months": ctx.king_months,
    }
