# Updating MediaKeeper

This guide explains how to update an existing MediaKeeper installation, switch between the stable and pre-release channels, and roll back if a release misbehaves. It targets self-hosters running the published image (`ghcr.io/keeperd93/mediakeeper`); source-built deployments follow the same shape, replacing the pull step with a rebuild.

> [!NOTE]
> All updates are non-destructive: the database, configuration and uploads live under `/data/` (or the volume you mounted there). Database migrations run automatically at boot via `alembic upgrade head`.

## Channels and tags

MediaKeeper publishes four kinds of image tags:

| Tag       | What it points to                                               | When it moves            |
| --------- | --------------------------------------------------------------- | ------------------------ |
| `:latest` | the most recent **stable** release (`vX.Y.Z` with no hyphen)    | each stable release      |
| `:beta`   | the most recent **pre-release** (`vX.Y.Z-rc.N`, `-beta.N`, ...) | each pre-release         |
| `:vX.Y.Z` | exactly that release                                            | immutable, never moves   |
| `:X.Y`    | the latest patch of the `X.Y` minor series (e.g. `:1.0`)        | each patch on that minor |

Choose your channel once, then update by pulling the same tag.

## Updating a running instance

The published image is consumed via `docker-compose.prod.yml`. The procedure is identical regardless of which floating tag you follow.

```sh
# 1. Pull the latest image for your channel
docker compose -f docker-compose.prod.yml pull

# 2. Re-create the container on top of the new image
docker compose -f docker-compose.prod.yml up -d

# 3. Watch the boot logs to confirm migrations applied cleanly
docker compose -f docker-compose.prod.yml logs -f --tail=200 mediakeeper
```

The new container reuses your existing `mk_data` volume, so settings, accounts, achievements, requests, and uploads are preserved. The startup runs Alembic migrations automatically; look for `alembic upgrade head` finishing without errors before you stop tailing the logs.

### Pinning an exact version

If you prefer reproducible upgrades, edit `docker-compose.prod.yml` and replace the floating tag with an immutable one:

```yaml
services:
  mediakeeper:
    image: ghcr.io/keeperd93/mediakeeper:v1.0.0 # pinned, immutable
```

Then run the same `pull` + `up -d` cycle. Future updates only happen when you change the pinned tag yourself.

## Switching channels

To move from stable to pre-release (or back):

```sh
# Edit docker-compose.prod.yml and change the image tag
#   ghcr.io/keeperd93/mediakeeper:latest  →  ghcr.io/keeperd93/mediakeeper:beta

docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

**Caveats when moving to `:beta`:**

- Pre-releases may ship database migrations not yet present on stable. Once you have run a `:beta` build, **rolling back to `:latest` is only safe if the stable release contains the same migration**, which is not guaranteed. Take a `:beta`-channel upgrade as a one-way step until the next stable catches up.
- Pre-release features are tested but not yet promoted to stable. Expect cosmetic or behavioural changes before the next stable release.

## Rolling back

If a release misbehaves, roll back to the previous immutable tag:

```sh
# 1. Identify the previous version you were running. Releases are listed at:
#    https://github.com/KeeperD93/mediakeeper/releases

# 2. Edit docker-compose.prod.yml and pin to that exact tag, e.g.:
#    image: ghcr.io/keeperd93/mediakeeper:v0.10.2

# 3. Pull + re-create
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

> [!WARNING]
> **Downgrades are not officially supported.** Migrations are forward-only by design; rolling back the image to a version older than the data schema can lead to broken behaviour or data loss. Always restore a backup of `/data/` taken **before** the upgrade you are rolling back from. See [`backup-restore.md`](backup-restore.md) for the backup procedure.

## What the release artifacts look like

Every published release produces:

- A multi-arch Docker image (`linux/amd64` + `linux/arm64`) pushed to GHCR under three or four tags as described above.
- A GitHub Release marked **Pre-release** for `-rc` / `-beta` tags, otherwise **Latest** for stable.
- A release notes body extracted from `CHANGELOG_EN.md` and `CHANGELOG_PORTAL_EN.md`, listing admin app changes and Portal changes side by side.

The full release notes for the version you are pulling are visible at <https://github.com/KeeperD93/mediakeeper/releases>.

## Updating a source-built deployment

If you cloned the repository and run `docker compose up -d` (with `build: .` from `docker-compose.yml`), update with:

```sh
git pull origin main
docker compose build mediakeeper
docker compose up -d
```

Migrations apply automatically the same way. This path always gives you the latest `main` branch, which is **ahead of every published release**: it may contain features that have not yet been tagged and shipped through the release pipeline.
