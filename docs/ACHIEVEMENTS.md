# MediaKeeper Achievements — how to add a trophy

This document is the step-by-step guide for adding, removing or modifying a
trophy. It does not describe the existing implementation in detail (the code
is short and readable) — it exists so a contributor can extend the catalogue
**without** introducing drift between definitions, checks, triggers, i18n
and the frontend.

> Every change to the catalogue must pass the guardrails described below
> (pytest meta-tests + boot-time validation). If the integrity test turns
> red in CI, the catalogue is broken — fix it before pushing.

---

## 1. System overview

```
┌─────────────────────────┐    ┌────────────────────────────┐
│ achievement_defs_*.py   │    │  achievements_seed.py      │
│  (declarative, static)  │ ─► │  upsert + prune in DB      │
└──────────┬──────────────┘    └────────────┬───────────────┘
           │                                │
           ▼                                ▼
┌─────────────────────────┐    ┌────────────────────────────┐
│ achievements_checks_*.py│ ◄─►│ check_all_achievements     │
│  (conditional logic per │    │ orchestrator, 5 passes,    │
│  condition_type)        │    │ try/except per pass        │
└─────────────────────────┘    └────────────┬───────────────┘
                                            │
                                            ▼
┌─────────────────────────┐    ┌────────────────────────────┐
│ Business service        │    │ safe_check_all_achievements│
│ (chat, lists, requests, │ ─► │ logged + silent wrapper    │
│  tickets, events, …)    │    │ source: "chat_message" …   │
└─────────────────────────┘    └────────────┬───────────────┘
                                            │
                                            ▼
                                ┌────────────────────────────┐
                                │ /api/portal/achievements/me│
                                │  → frontend trophy panel   │
                                └────────────────────────────┘
```

- **Definitions** (`achievement_defs_*.py`): pure data, no cross-imports with
  the checks. A trophy = a unique `id` + a `condition_type` + tiers.
- **Checks** (`achievements_checks_*.py`): the logic that turns raw data
  (Emby sessions, user lists, pending requests, …) into `progress`. One
  check function per major domain.
- **Orchestrator** (`check_all_achievements`): runs the 5 check passes
  sequentially. Each pass is isolated with try/except — a regression in one
  pass does not break the others nor the final commit.
- **Wrapper** (`safe_check_all_achievements`): the single entry point for
  every business service. Logs `{user_id, source, duration_ms, unlocks}`
  per call. The variant `safe_check_all_achievements_in_new_session` is for
  `BackgroundTasks` that run outside of the HTTP session.

---

## 2. Add a standard trophy (tiered or standalone)

### 2.1 Define

Add one (or more) entries to `STANDARD_DEFS` in
`backend/services/portal/achievement_defs_standard.py`:

```python
{"id": "curator_1", "category": "community",
 "name_key": "portal.achievements.curator",
 "description_key": "portal.achievements.curator_desc",
 "icon": "Bookmark",
 "tier": 1, "xp_reward": 20, "threshold": 1,
 "condition_type": "lists_public_created",
 "next_tier_id": "curator_2",
 "secret": False, "sort_order": 300},
```

Conventions:

| Field            | Rule                                                     |
|------------------|----------------------------------------------------------|
| `id`             | English snake_case (`curator_1`, `librarian_3`).         |
| `name_key`       | `portal.achievements.<camelCase>` (one per family).      |
| `description_key`| `portal.achievements.<camelCase>_desc`.                  |
| `icon`           | Lucide name (`Bookmark`, `Library`, `Star`, …).          |
| `tier`           | 1 (Bronze) → 6 (Mythic). Tier 6 is reserved for "finale" families. |
| `xp_reward`      | Standard scale `20 / 50 / 110 / 220 / 500 / 1200`.       |
| `threshold`      | Strictly increasing along the chain (except whitelisted exception — `competitor`). |
| `condition_type` | A logical identifier shared by every tier of a family.   |
| `next_tier_id`   | The `id` of the next tier, or `None` for the last.       |
| `sort_order`     | Block of 10 per family (300, 310, …) to leave room.      |

### 2.2 Implement the `condition_type`

Pick the right check module depending on the domain:

| Module                                  | Domain                                              |
|-----------------------------------------|-----------------------------------------------------|
| `achievements_checks_standard.py`       | Emby sessions (movies, series, languages, marathons). |
| `achievements_checks_progression.py`    | Leaderboard, level, profile, community, lists.      |
| `achievements_checks_secrets_a/b.py`    | Secrets tied to specific conditions.                |
| `achievements_checks_meta.py`           | Special case `condition_type="meta"` only.          |

Add a branch like:

```python
if "lists_public_created" in by_type:
    val = (await db.execute(
        select(func.count(UserList.id)).where(
            UserList.user_id == user_id,
            UserList.is_deleted.is_(False),
            UserList.privacy.in_((PRIVACY_PUBLIC_READONLY, PRIVACY_COLLABORATIVE)),
        )
    )).scalar() or 0
    await _apply("lists_public_created", val)
```

`_apply` (already provided in the module) handles idempotency and the XP
grant.

### 2.3 Register the `condition_type` in the known list

Edit `backend/services/portal/achievements_validation.py` to add the new
`condition_type` to `KNOWN_CONDITION_TYPES`. Without this step, the
meta-test `find_orphan_condition_types` turns red.

### 2.4 Wire the trigger

Identify the service that mutates the data (create a list, send a message,
…) and call the wrapper **after the commit**:

- From an **API endpoint**: prefer `BackgroundTasks` to avoid slowing the
  response:

  ```python
  background_tasks.add_task(
      safe_check_all_achievements_in_new_session,
      user.id, user.username, "list_created",
  )
  ```

- From a **server-side service** (e.g. `lists.create_list`): direct call,
  the wrapper is silent by default:

  ```python
  await safe_check_all_achievements(db, user_id, None, source="list_created")
  ```

No duplication: one trigger per operation. If several trophies depend on
the same operation, the runner sweeps them all in a single call.

### 2.5 i18n FR + EN

In `frontend/src/locales/fr.json` **and** `frontend/src/locales/en.json`,
under `portal.achievements`:

```jsonc
"curator": "Curateur",
"curator_desc": "Listes publiques partagées avec la communauté",
```

(EN equivalent.) The meta-test
`test_every_definition_has_fr_and_en_translations` verifies that every
`name_key` / `description_key` resolves in both languages.

### 2.6 pytest test

Add a test in `backend/tests/test_achievements_phase1.py` (or a dedicated
file if the family has several special cases):

```python
@pytest.mark.asyncio
async def test_first_public_list_unlocks_curator_bronze(db_session):
    user, _ = await _make_user_and_profile(db_session)
    await seed_achievements(db_session)

    await lists_svc.create_list(
        db_session, user.id,
        {"name": "Best of 2025", "privacy": PRIVACY_PUBLIC_READONLY},
    )

    assert await _ach_unlocked(db_session, user.id, "curator_1")
```

### 2.7 Portal changelog (FR + EN)

Under `[Unreleased] > Added` in `backend/CHANGELOG_PORTAL_FR.md` **and**
`backend/CHANGELOG_PORTAL_EN.md`, following the brevity rule (≤ 12 words,
user-facing language, no technical jargon).

---

## 3. Add a secret trophy

Same steps as §2, plus:

1. Define in `SECRET_DEFS` (not `STANDARD_DEFS`) with `secret: True`.
2. Add an entry to `SECRET_THEMES` (maps the `id` to a CSS theme name —
   `xmas`, `halloween`, etc.).
3. If the thematic category is not `secret`, fill in
   `SECONDARY_CATEGORIES` so the secret also shows up in the target
   category (special / dedication / watching / …).
4. Add the visual rendering in
   `frontend/src/components/portal/profile/TrophyFx.vue`: a thematic CSS
   block (particles, halo, …) for the new key. Without that block, the
   unlock will render as a generic glowing icon but without signature.
5. (Optional) If the secret unlocks a title, add it to `TITLE_REWARDS`.

The meta-test `test_every_secret_has_a_theme_mapping` enforces that no
secret is left without a CSS theme.

---

## 4. Modify an existing trophy

- **`threshold`** or **`xp_reward`**: transparent change at seed time.
  Users already unlocked stay unlocked (the seed never resets `unlocked`
  to `false`). New users must reach the new threshold.
- **`condition_type`**: avoid — invalidates existing progress. Prefer
  creating a new family.
- **`next_tier_id`**: change supported; the seed updates the chain in pass
  2 without touching individual progress.
- **`category`**: impacts the category's meta-master (automatic
  recomputation of the matching meta's `threshold` at the next seed).

---

## 5. Remove a trophy

Delete the corresponding entry from `*_DEFS`. At the next boot:

1. `seed_achievements` (pass 3) deletes the `Achievement` row plus every
   associated `UserAchievement` (cascade `ON DELETE CASCADE`).
2. The frontend no longer sees the trophy in the `/me` payload.
3. Boot-time validation passes (the `id` no longer exists, so no orphan
   reference).

> Before the v1.0 release, the DB is disposable (cf. project policy) — no
> Alembic migration is needed for a removal. Post-v1.0, removals must go
> through an explicit migration if history matters.

---

## 6. Conventions

| Aspect                     | Convention                                                |
|----------------------------|-----------------------------------------------------------|
| Slugs                      | English `snake_case` (`movie_buff_3`, `secret_christmas`).|
| i18n                       | `portal.achievements.<camelCase>` + `_desc` twin.         |
| Standard XP scale          | `20 / 50 / 110 / 220 / 500 / 1200`.                       |
| `sort_order`               | Block of 10 per family for headroom.                      |
| Max tier                   | 6 (Mythic) — reserved for "finale" families.              |
| Increasing thresholds      | Strict, except whitelist `_NON_MONOTONIC_FAMILIES`.       |
| Trigger source label       | Short, `snake_case` (`chat_message`, `list_created`).     |

---

## 7. Guardrails

| Mechanism                                                       | When                  | Effect                  |
|-----------------------------------------------------------------|-----------------------|-------------------------|
| `backend/tests/test_achievements_integrity.py`                  | CI / `pytest`         | Fail-loud on drift.     |
| `_validate_definitions()` in `achievements_seed.py`             | Dev / test boot       | Refuses to seed.        |
| `_validate_definitions()` in prod (`ENV=production`)            | Prod boot             | Log + continue.         |
| `_safe_pass` in `check_all_achievements`                        | Runtime               | One failed pass does not break the others. |
| `safe_check_all_achievements` (silent by default)               | Business triggers     | A runner regression does not break the origin endpoint. |

The meta-test covers:

- no duplicated `id` across the three `*_DEFS`;
- every declared `condition_type` is implemented;
- every `next_tier_id` points to an existing `id`;
- strictly increasing thresholds per chain (except whitelist);
- every secret has its `SECRET_THEMES` entry;
- every meta targets a non-empty category;
- every `name_key` / `description_key` has FR + EN translations;
- `EXCLUSIVE_FROM_META` and `PLACEHOLDER_IDS` only reference existing
  `id`s.

If the suite passes and boot does not complain, the catalogue is
consistent.

---

## 8. Placeholders

Some trophies have a check branch that always returns `0` because the
required data is not yet available (e.g. TMDB production year, real-time
concurrent sessions, `XpLedger` aggregate not yet wired). They are listed
in `PLACEHOLDER_IDS` (`achievement_defs_constants.py`).

Consequences:

- The runner **ignores** them (saves queries).
- `get_achievements_for_profile` **excludes** them from the `total_count`
  exposed to the frontend, so the global progress percentage reflects only
  what is actually reachable.
- The `Achievement` row stays in the DB to preserve any historical
  `UserAchievement` rows.

When a placeholder is implemented for real:

1. Remove its `id` from `PLACEHOLDER_IDS`.
2. Replace the `await _apply(..., 0)` branch with the real logic.
3. Update this document (this section).
4. The meta-test passes automatically (no specific change required for
   this `id`).

---

## 9. Antipatterns to avoid

- **Frontend-side trigger**: the frontend detects unlocks via
  `unlocked_at < 5 minutes` at profile load time. No WebSocket, no
  polling. If a real-time use case becomes necessary, it is a dedicated
  effort to be decided as a future architecture change.
- **Internal EventBus**: considered then deferred. For ~10 trigger
  callsites, the indirection costs more than the benefits. Reassess
  post-v1.0 if the number of subscribers (Discord notifications per
  business event, dedicated audit log, …) exceeds 2.
- **Duplicating a `condition_type`** across two families: `audio_languages`
  is shared between `globe_trotter_*` and `world_palette_*`. This is
  intentional — two families, two scales, same signal. But do not
  multiply the pattern: when possible, distinguish via a new dedicated
  `condition_type`.
- **Modifying a seed already applied**: `seed_achievements` is
  re-entrant; you change the definitions, you re-run, that is all. No
  dedicated Alembic migration as long as the DB is disposable
  (pre-v1.0).
