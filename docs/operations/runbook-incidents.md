# Incident response runbook

> **Audience.** This runbook is for the operator on the keyboard at 3 a.m.
> when the application is on fire. It assumes you have shell access to the
> deployment host, the latest code checkout, and the most recent backup
> ZIP within reach.
>
> **Scope.** Three critical disaster-recovery scenarios:
> (1) database corruption, (2) loss or theft of the host running the
> application, (3) a bad deployment that needs to be rolled back.
>
> **Out of scope.** Restore *commands* (those live in
> [`backup-restore.md`](backup-restore.md), already validated end-to-end).
> Vulnerability disclosure (see [`SECURITY.md`](../../SECURITY.md)).
> Off-site recovery flow — **not operational at this stage**, see
> [`backup-restore.md` §8](backup-restore.md).

---

## 1. Quick triage (≤ 30 seconds)

When something is clearly broken, ask three questions before doing
anything else. The answers route you to the right scenario; do not
mix scenarios.

```
                ┌──────────────────────────────────┐
                │ Is the host reachable at all?    │
                │ (SSH OK, DSM/control panel OK,   │
                │  ping OK)                        │
                └──────────────────────────────────┘
                       │                    │
                      YES                   NO
                       │                    │
                       ▼                    ▼
        ┌──────────────────────┐   ┌─────────────────────┐
        │ Did the symptoms     │   │ Go to §3 — Host     │
        │ start right after a  │   │ loss / theft.       │
        │ rebuild or a merge?  │   └─────────────────────┘
        └──────────────────────┘
            │             │
           YES            NO
            │             │
            ▼             ▼
  ┌─────────────────┐  ┌──────────────────────┐
  │ Go to §4 — Bad  │  │ Go to §2 — Database  │
  │ deployment.     │  │ corruption / loss.   │
  └─────────────────┘  └──────────────────────┘
```

**Common pre-requisites for any scenario** (gather before acting):

- A terminal on the operator host with `unzip`, `ssh`/`scp`, and Docker
  available (see [`backup-restore.md` §3](backup-restore.md)).
- The most recent backup ZIP (`mediakeeper_backup_*.zip`) located and
  copied off the production host.
- A scratch buffer for the incident timeline — a plain text file works.
  Start it now; you will need it for the post-mortem (§5.3).

> ⚠️ **Do not loop on auto-restart.** If the application container is
> in a restart loop, stop it before investigating. Repeated boot
> attempts on a corrupted database can extend the damage.

---

## 2. Scenario — Database corruption or loss

### 2.1 Symptoms

- Application container fails to boot (exit code ≠ 0 on `docker logs`).
- `alembic upgrade head` errors with schema-level messages.
- `[ENCRYPTION] Failed to decrypt a value` floods the logs.
- `/api/health` returns 5xx persistently; Docker healthcheck flips
  the container to **UNHEALTHY**.
- `psql: FATAL: database "mediakeeper_db" does not exist` or
  `relation "users" does not exist`.

### 2.2 Immediate mitigation

1. **Stop the container** (no auto-restart loop):
   ```bash
   docker stop mediakeeper
   ```
2. **Snapshot the logs** before they roll over:
   ```bash
   docker logs --tail 500 mediakeeper > incident-logs.txt
   ```
3. **Identify the most recent valid backup ZIP**. Check the manifest
   first (does not extract the secret material):
   ```bash
   unzip -p <backup>.zip manifest.json | jq '.version, .components.pg_dump, .encryption_key.status'
   ```
   Expect `"1.1"`, `true`, `"included"`. If any of those are wrong,
   pick the previous ZIP and try again.

### 2.3 Recovery procedure

The full step-by-step recovery commands are documented in
[`backup-restore.md` §3 → §5](backup-restore.md). Do **not** improvise
a parallel procedure here.

The two paths:

- **Practice run on a disposable container** — use
  [`backup-restore.md` §4](backup-restore.md). Recommended whenever you
  are not sure the ZIP is intact.
- **Real recovery into production** — use
  [`backup-restore.md` §5](backup-restore.md). The Fernet key must
  land on disk *before* the application boots.

### 2.4 Post-recovery validation

Run the checklist in [`backup-restore.md` §6](backup-restore.md). It
covers the Alembic version, row counts, Fernet decryption smoke test,
outbound integrations, and absence of decryption errors in the
post-recovery logs.

---

## 3. Scenario — Host loss or theft (full wipe)

### 3.1 Symptoms

- The deployment host is unreachable on every channel
  (SSH timeout, ICMP timeout, control panel down, no power).
- The storage layer reports a degraded or missing array
  (RAID failed, drives missing).
- The host has been physically removed (theft, hardware confiscation,
  fire, water damage).

### 3.2 Immediate mitigation

1. **Confirm the loss is real.** Distinguish a network outage from an
   actual host failure. Try a second route (mobile network, neighbour
   Wi-Fi, console access) before declaring loss.
2. **If theft is confirmed**, rotate the credentials of any external
   account that could be reached from the stolen host (Emby admin
   password, third-party API keys configured in the application).
   These rotations happen on the upstream services, not in
   MediaKeeper.
3. **Check whether an off-site backup target was configured.**

> ⚠️ **R4 — Off-site is not operational at this stage.** Until v1.0,
> the database is intentionally treated as disposable and no off-site
> replication target is in place. See
> [`backup-restore.md` §8](backup-restore.md). If the host is gone and
> the only ZIPs were on it, the data is **not recoverable** from
> within MediaKeeper. Be transparent with the affected users.

### 3.3 Recovery procedure (only if an off-site copy exists)

If — and only if — a ZIP from an off-site target is available:

1. Provision a new host (replacement NAS, temporary Docker server,
   spare hardware) and follow the standard
   [`README.md` quick start](../../README.md).
2. Retrieve the most recent off-site ZIP onto the new host, treat it
   as a secret (see
   [`backup-restore.md` §3 warning](backup-restore.md)).
3. Run the *real* recovery flow from
   [`backup-restore.md` §5](backup-restore.md), not the drill flow.
4. Update the URL or DNS pointing at the application so users land on
   the new instance.

If no off-site copy exists, document the loss in the incident file,
move directly to §5.3 (post-mortem) and recreate a fresh deployment
from `README.md` with an empty database.

### 3.4 Post-recovery validation

[`backup-restore.md` §6](backup-restore.md) plus one host-specific
check: confirm the new endpoint is announced to users and that any
external service (Emby, OAuth providers) accepts the new origin if
relevant.

---

## 4. Scenario — Bad deployment / failed rollout

### 4.1 Symptoms

- Right after a rebuild or a `docker compose up -d`:
  `/api/health` returns 5xx.
- The frontend renders blank or shows a JS error referencing a route
  that no longer exists.
- `alembic upgrade head` fails at boot with a schema mismatch error
  (often when `MK_DB_SCHEMA_MODE=validate` rejects the schema).
- A user-facing feature regressed visibly.
- The Fernet warning in the docstring of `restore_backup` was not
  followed during a partial restore (see
  [`backup-restore.md` §1](backup-restore.md)).

### 4.2 Immediate mitigation

1. **Read the logs first** — the failure mode tells you whether code
   alone broke or whether a migration ran:
   ```bash
   docker logs --tail 200 mediakeeper
   ```
2. **Identify the last known-good commit on `origin/main`** using the
   public history:
   ```bash
   git log --oneline origin/main
   ```
3. **Decide between three rollback paths** before touching anything
   else:
   - **Case A — code only.** Migration did not run, or ran cleanly
     and is forward-compatible. Re-deploy the previous tag.
   - **Case B — code + database.** A destructive migration ran and
     needs to be undone. Requires a backup ZIP taken *before* the
     deployment.
   - **Case C — non-recoverable without backup.** A destructive
     migration ran and no pre-deployment ZIP exists. Stop, escalate
     to §5.1, and weigh whether to restore from the most recent ZIP
     (accepting data loss) or to forward-fix.

### 4.3 Rollback procedure

**Case A — code only:**

```bash
# On the build host:
git checkout <last-good-commit>
# Sync to the deployment host (deployment is not automatic, see
# backup-restore.md §8), then:
docker compose build && docker compose up -d
```

**Case B — code + database:**

1. Stop the container (`docker stop mediakeeper`).
2. Restore the pre-deployment ZIP using
   [`backup-restore.md` §5](backup-restore.md) (full procedure: SQL
   dump replay + Fernet key in place + optional applicative restore).
3. Roll back the code as in Case A.
4. Start the container; the next `alembic upgrade head` should be a
   no-op against the restored schema.

**Case C — non-recoverable without backup:**

Document the situation, notify affected users transparently, and
choose between two equally lossy options:

- Restore the most recent ZIP available (accepts the data loss
  between the ZIP and the failed deployment).
- Keep the broken deployment and forward-fix with a corrective
  migration (accepts the time-to-fix as user-facing downtime).

### 4.4 Post-recovery validation

- `/api/health` returns 200 within the healthcheck timeout.
- Admin login works and the affected feature behaves as before.
- For Case B: `alembic_version` matches the code being deployed.
- No `[ENCRYPTION] Failed to decrypt a value` lines in the post-restart
  logs.
- Spot-check one outbound integration (Emby session list, an
  OpenSubtitles search, or a Discord webhook) to confirm encrypted
  settings decrypted cleanly.

---

## 5. Common procedures

### 5.1 Operator contacts and ownership

Fill in your own deployment specifics. Keep this section in a private
copy if it carries personal data; the public template uses
placeholders only.

| Role | Contact | Notes |
|---|---|---|
| Primary operator | `<OPERATOR_NAME>` / `<OPERATOR_EMAIL>` / `<OPERATOR_PHONE>` | First point of contact at any hour. |
| Secondary operator | `<SECONDARY_OPERATOR>` | Optional — covers the primary's absence. |
| Hosting provider support | `<HOST_PROVIDER_SUPPORT>` | Vendor support line for the host (NAS vendor, hosting vendor, etc.). |
| Network / ISP support | `<ISP_SUPPORT>` | Useful in §3 to distinguish a host outage from a network outage. |
| User community channel | `<USER_NOTIFICATION_CHANNEL>` | Where you tell users an incident is in progress. |
| Security disclosure | See [`SECURITY.md`](../../SECURITY.md) | Use the SECURITY policy for vulnerability reports, not this runbook. |

### 5.2 Post-incident checklist

Run through this once the application is stable again:

- [ ] All checks in §2.4 / §3.4 / §4.4 (whichever applies) green.
- [ ] Incident timeline written down while still fresh
      (use the scratch buffer started in §1).
- [ ] Users notified of the resolution on
      `<USER_NOTIFICATION_CHANNEL>`.
- [ ] Any rotated credential (§3.2) re-injected into the application
      via the admin settings.
- [ ] If a backup was used, verify the next scheduled backup runs
      and produces a fresh ZIP.
- [ ] If a deployment was rolled back (§4), open a follow-up issue or
      task to address the root cause before re-attempting the
      deployment.
- [ ] Schedule the post-mortem within seven days (§5.3).

### 5.3 Post-mortem template

Filled post-mortems are kept **private** to avoid leaking user data
and operational details. The template below is the public skeleton;
copy it into your private notes.

```markdown
# Post-mortem — <incident-id>

## Timeline (UTC, ISO 8601)
- YYYY-MM-DDTHH:MM:SSZ — Symptom first observed.
- YYYY-MM-DDTHH:MM:SSZ — Operator paged / noticed.
- YYYY-MM-DDTHH:MM:SSZ — Mitigation started.
- YYYY-MM-DDTHH:MM:SSZ — Service restored.
- YYYY-MM-DDTHH:MM:SSZ — Confirmation (post-recovery checks green).

## Scenario
Pick one: §2 DB corruption / §3 host loss / §4 bad deployment.

## Root cause
What actually broke and why.

## Impact
- Duration of degraded service:
- Users affected:
- Data loss (rows, time window):

## Fix
What was done to restore service. Reference §X.Y of this runbook.

## Prevention
What should change so the same incident does not recur. Concrete
follow-ups, not vague intentions.
```

---

## 6. Out of scope

The following situations exist but are *not* covered by this runbook;
they each have their own home.

- **Vulnerability disclosure or active exploitation.** Use
  [`SECURITY.md`](../../SECURITY.md). Do not improvise public
  communication during an exploitation event; coordinate with the
  disclosure channel.
- **User account compromise** without server-side compromise. Reset
  the affected account through the admin UI; if the breach was
  caused by a flaw in MediaKeeper, route the report through
  [`SECURITY.md`](../../SECURITY.md).
- **Off-site recovery.** Off-site replication is reported as
  intentionally not configured pre-v1.0
  ([`backup-restore.md` §8](backup-restore.md)). Once it is in place
  in a future version, the §3.3 flow will be updated to reference
  the actual procedure.
- **Performance incidents** (slowness without crash). Outside the
  three DR scenarios this runbook covers; see future monitoring
  documentation when it lands.

---

## 7. See also

- [`backup-restore.md`](backup-restore.md) — operator restore
  procedure, validated end-to-end. Centrally referenced from §2, §3
  and §4 of this runbook.
- [`SECURITY.md`](../../SECURITY.md) — vulnerability disclosure
  policy, supported versions, scope and safe-harbour.
- [`ARCHITECTURE.md`](../../ARCHITECTURE.md) — code map, boot
  pipeline, encryption-at-rest layer, schema validation mode
  (`MK_DB_SCHEMA_MODE`).
- [`README.md`](../../README.md) — quick start for provisioning a
  fresh deployment after §3.3.
