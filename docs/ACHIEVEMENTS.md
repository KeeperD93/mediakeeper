# MediaKeeper Achievements — workflow d'ajout

Ce document est le mode d'emploi à suivre pour ajouter, retirer ou modifier
un trophée. Il ne décrit pas l'implémentation existante en détail (le code
est court et lisible) — il existe pour qu'un contributeur puisse étendre le
catalogue **sans** introduire de drift entre les définitions, les checks,
les triggers, l'i18n et le frontend.

> Toute évolution du catalogue passe par les garde-fous décrits plus bas
> (méta-test pytest + validation au boot). Si le test d'intégrité tombe en
> rouge en CI, le catalogue est cassé — corrige avant de pousser.

---

## 1. Vue d'ensemble du système

```
┌─────────────────────────┐    ┌────────────────────────────┐
│ achievement_defs_*.py   │    │  achievements_seed.py      │
│  (déclaratif, statique) │ ─► │  upsert + prune en DB      │
└──────────┬──────────────┘    └────────────┬───────────────┘
           │                                │
           ▼                                ▼
┌─────────────────────────┐    ┌────────────────────────────┐
│ achievements_checks_*.py│ ◄─►│ check_all_achievements     │
│  (logique conditionnelle│    │ orchestrateur, 5 passes    │
│  par condition_type)    │    │ try/except par passe       │
└─────────────────────────┘    └────────────┬───────────────┘
                                            │
                                            ▼
┌─────────────────────────┐    ┌────────────────────────────┐
│ Service métier          │    │ safe_check_all_achievements│
│ (chat, lists, requests, │ ─► │ wrapper logué + silent     │
│  tickets, events, …)    │    │ source: "chat_message" …   │
└─────────────────────────┘    └────────────┬───────────────┘
                                            │
                                            ▼
                                ┌────────────────────────────┐
                                │ /api/portal/achievements/me│
                                │  → frontend trophy panel   │
                                └────────────────────────────┘
```

- **Définitions** (`achievement_defs_*.py`) : données pures, aucun import
  croisé avec les checks. Un trophée = un `id` unique + un `condition_type` +
  des paliers.
- **Checks** (`achievements_checks_*.py`) : la logique qui transforme une
  donnée brute (sessions Emby, listes utilisateur, requêtes pendantes, …)
  en `progress`. Une fonction de check par grand domaine.
- **Orchestrateur** (`check_all_achievements`) : exécute les 5 passes de
  check séquentiellement. Chaque passe est isolée par try/except — une
  régression dans une passe ne casse pas les autres ni le commit final.
- **Wrapper** (`safe_check_all_achievements`) : un seul point d'entrée pour
  tous les services métier. Logue `{user_id, source, duration_ms, unlocks}`
  par appel. Variante `safe_check_all_achievements_in_new_session` pour
  les `BackgroundTasks` qui s'exécutent hors de la session HTTP.

---

## 2. Ajouter un trophée standard (tiéré ou standalone)

### 2.1 Définir

Ajouter une (ou plusieurs) entrée(s) à `STANDARD_DEFS` dans
`backend/services/portal/achievement_defs_standard.py` :

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

Conventions :

| Champ            | Règle                                                     |
|------------------|-----------------------------------------------------------|
| `id`             | snake_case anglais (`curator_1`, `librarian_3`).          |
| `name_key`       | `portal.achievements.<camelCase>` (un par famille).       |
| `description_key`| `portal.achievements.<camelCase>_desc`.                   |
| `icon`           | nom Lucide (`Bookmark`, `Library`, `Star`, …).            |
| `tier`           | 1 (Bronze) → 6 (Mythique). Réservé tier 6 aux familles « finale ». |
| `xp_reward`      | barème standard `20 / 50 / 110 / 220 / 500 / 1200`.       |
| `threshold`      | strictement croissant le long de la chaîne (sauf exception whitelistée — `competitor`). |
| `condition_type` | un identifiant logique partagé par tous les tiers d'une famille. |
| `next_tier_id`   | `id` du tier suivant, ou `None` pour le dernier.          |
| `sort_order`     | bloc de 10 par famille (300, 310, …) pour laisser de la place. |

### 2.2 Implémenter le `condition_type`

Choisir le bon module check en fonction du domaine :

| Module                                  | Domaine                                             |
|-----------------------------------------|------------------------------------------------------|
| `achievements_checks_standard.py`       | sessions Emby (films, séries, langues, marathons).  |
| `achievements_checks_progression.py`    | leaderboard, niveau, profil, communauté, listes.    |
| `achievements_checks_secrets_a/b.py`    | secrets liés à des conditions précises.             |
| `achievements_checks_meta.py`           | cas spécial `condition_type="meta"` uniquement.     |

Ajouter une branche du type :

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

`_apply` (déjà fourni dans le module) gère l'idempotence et le grant XP.

### 2.3 Inscrire le `condition_type` à la liste connue

Éditer `backend/services/portal/achievements_validation.py` pour ajouter
le nouveau `condition_type` dans `KNOWN_CONDITION_TYPES`. Sans cette étape,
le méta-test `find_orphan_condition_types` tombe rouge.

### 2.4 Câbler le trigger

Identifier le service qui modifie la donnée (créer une liste, envoyer un
message, …) et appeler le wrapper **après le commit** :

- Depuis un **endpoint API** : préférer `BackgroundTasks` pour ne pas
  ralentir la réponse :

  ```python
  background_tasks.add_task(
      safe_check_all_achievements_in_new_session,
      user.id, user.username, "list_created",
  )
  ```

- Depuis un **service** côté serveur (par ex. `lists.create_list`) : appel
  direct, le wrapper est silent par défaut :

  ```python
  await safe_check_all_achievements(db, user_id, None, source="list_created")
  ```

Pas de duplication : un seul trigger par opération. Si plusieurs trophées
dépendent de la même opération, le runner les balaie tous en un appel.

### 2.5 i18n FR + EN

Dans `frontend/src/locales/fr.json` **et** `frontend/src/locales/en.json`,
sous `portal.achievements` :

```jsonc
"curator": "Curateur",
"curator_desc": "Listes publiques partagées avec la communauté",
```

(EN équivalent.) Le méta-test `test_every_definition_has_fr_and_en_translations`
vérifie que chaque `name_key` / `description_key` est résolvable dans les
deux langues.

### 2.6 Test pytest

Ajouter un test dans `backend/tests/test_achievements_phase1.py` (ou un
fichier dédié si la famille a plusieurs cas spéciaux) :

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

### 2.7 Changelog Portal (FR + EN)

Sous `[Unreleased] > Added` dans `backend/CHANGELOG_PORTAL_FR.md` **et**
`backend/CHANGELOG_PORTAL_EN.md`, en respectant la règle Emby
(≤ 12 mots, langage utilisateur, pas de jargon technique).

---

## 3. Ajouter un trophée secret

Mêmes étapes que §2, plus :

1. Définir dans `SECRET_DEFS` (pas `STANDARD_DEFS`) avec `secret: True`.
2. Ajouter une entrée dans `SECRET_THEMES` (mappe l'`id` à un nom de thème
   CSS — `xmas`, `halloween`, etc.).
3. Si la catégorie thématique n'est pas `secret`, renseigner
   `SECONDARY_CATEGORIES` pour que le secret apparaisse aussi dans la
   catégorie cible (special / dedication / watching / …).
4. Ajouter le rendu visuel dans
   `frontend/src/components/portal/profile/TrophyFx.vue` : un bloc CSS
   thématique (particules, halo, …) pour la nouvelle clé. Sans ce bloc,
   le déblocage rendra une icône glow générique mais sans signature.
5. (Optionnel) Si le secret débloque un titre, l'ajouter à `TITLE_REWARDS`.

Le méta-test `test_every_secret_has_a_theme_mapping` impose qu'aucun secret
ne traîne sans thème CSS.

---

## 4. Modifier un trophée existant

- **Threshold** ou **xp_reward** : changement transparent au seed. Les
  utilisateurs déjà débloqués restent débloqués (le seed ne remet jamais
  `unlocked` à `false`). Les nouveaux doivent atteindre le nouveau seuil.
- **`condition_type`** : à éviter — invalide la progression existante.
  Préférer la création d'une nouvelle famille.
- **`next_tier_id`** : changement supporté ; le seed met à jour la chaîne
  en passe 2 sans toucher aux progressions individuelles.
- **`category`** : impact sur le méta-master de la catégorie (recalcul
  automatique du `threshold` du méta correspondant au seed suivant).

---

## 5. Retirer un trophée

Supprimer l'entrée correspondante des `*_DEFS`. Au prochain boot :

1. `seed_achievements` (passe 3) supprime la ligne `Achievement` ainsi que
   toutes les `UserAchievement` associées (cascade `ON DELETE CASCADE`).
2. Le frontend ne voit plus le trophée dans le payload `/me`.
3. La validation au boot passe (l'`id` n'existe plus, donc pas de
   référence orpheline).

> Avant la sortie v1.0, la DB est jetable (cf. policy projet) — pas
> besoin de migration Alembic pour un retrait. Post-v1.0, les retraits
> doivent passer par une migration explicite si l'historique compte.

---

## 6. Conventions

| Aspect                     | Convention                                                |
|----------------------------|------------------------------------------------------------|
| Slugs                      | `snake_case` anglais (`movie_buff_3`, `secret_christmas`). |
| i18n                       | `portal.achievements.<camelCase>` + `_desc` jumelé.        |
| XP barème standard         | `20 / 50 / 110 / 220 / 500 / 1200`.                        |
| `sort_order`               | bloc de 10 par famille pour laisser de la marge.           |
| Tier max                   | 6 (Mythique) — réservé aux familles « finales ».           |
| Threshold croissant        | strictement, sauf whitelist `_NON_MONOTONIC_FAMILIES`.     |
| Trigger source label       | court, en `snake_case` (`chat_message`, `list_created`).   |

---

## 7. Garde-fous

| Mécanisme                                                        | Quand                  | Effet                  |
|------------------------------------------------------------------|------------------------|-------------------------|
| `backend/tests/test_achievements_integrity.py`                   | CI / `pytest`          | Fail-loud sur drift.    |
| `_validate_definitions()` dans `achievements_seed.py`            | Boot dev / test        | Refuse de seed.         |
| `_validate_definitions()` en prod (`ENV=production`)             | Boot prod              | Log + continue.         |
| `_safe_pass` dans `check_all_achievements`                       | Runtime                | Une passe en échec ne casse pas les autres. |
| `safe_check_all_achievements` (silent par défaut)                | Triggers métier        | Une régression du runner ne casse pas l'endpoint d'origine. |

Le méta-test couvre :

- pas d'`id` dupliqué entre les trois `*_DEFS` ;
- chaque `condition_type` déclaré est implémenté ;
- chaque `next_tier_id` pointe vers un `id` existant ;
- thresholds strictement croissants par chaîne (sauf whitelist) ;
- chaque secret a son entrée `SECRET_THEMES` ;
- chaque méta cible une catégorie non vide ;
- chaque `name_key` / `description_key` a une traduction FR + EN ;
- `EXCLUSIVE_FROM_META` et `PLACEHOLDER_IDS` ne référencent que des `id`
  existants.

Si la suite passe et le boot ne se plaint pas, le catalogue est cohérent.

---

## 8. Placeholders

Certains trophées ont une branche check qui retourne toujours `0` parce
que la donnée nécessaire n'est pas encore disponible (par ex. année de
production TMDB, sessions concurrentes en temps réel, agrégat sur
`XpLedger` non encore branché). Ils sont listés dans
`PLACEHOLDER_IDS` (`achievement_defs_constants.py`).

Conséquences :

- Le runner les **ignore** (économise les requêtes).
- `get_achievements_for_profile` les **exclut** du `total_count` exposé
  au frontend, donc le pourcentage de progression global reflète
  uniquement ce qui est réellement atteignable.
- La ligne `Achievement` reste dans la DB pour préserver les
  `UserAchievement` historiques éventuels.

Quand un placeholder est implémenté pour de vrai :

1. Retirer son `id` de `PLACEHOLDER_IDS`.
2. Remplacer la branche `await _apply(..., 0)` par la logique réelle.
3. Mettre à jour ce document (cette section).
4. Le méta-test passe automatiquement (il ne réclame pas de changement
   spécifique pour cet `id`).

---

## 9. Antipattern à éviter

- **Trigger côté frontend** : le frontend détecte les unlocks via
  `unlocked_at < 5 minutes` au moment du chargement profil. Pas de
  WebSocket, pas de polling. Si un usage temps réel devient nécessaire,
  c'est un chantier dédié (voir audit Phase 0).
- **EventBus interne** : envisagé puis différé. Pour ~10 callsites de
  trigger, l'indirection coûte plus que les bénéfices. À réévaluer
  post-v1.0 si le nombre de subscribers (notifications Discord par
  événement métier, audit log dédié, …) dépasse 2.
- **Dupliquer un `condition_type`** entre deux familles : l'audit a
  identifié `audio_languages` partagé par `globe_trotter_*` et
  `world_palette_*`. C'est volontaire — deux familles, deux barèmes,
  même signal. Mais ne pas multiplier ce pattern : si possible, distinguer
  par un nouveau `condition_type` dédié.
- **Modifier un seed appliqué** : `seed_achievements` est ré-entrant ;
  on modifie les définitions, on relance, c'est tout. Pas de migration
  Alembic dédiée tant que la DB est jetable (avant v1.0).
