# Runtime monitoring — webhook alerts

MediaKeeper can push runtime alerts to a webhook when something
critical happens inside the container. The feature is fully **opt-in**:
without configuration nothing is sent.

This document explains what is reported, how to enable it, how the
debounce works and how to troubleshoot delivery problems.

---

## 1. What gets reported

Six categories of incidents are pushed to the webhook. Each category
has its own deduplication key, so a flapping component cannot block
unrelated alerts.

| Category | When it fires | Severity |
|---|---|---|
| `db_unavailable` | The internal liveness probe failed twice in a row (~10 minutes) | Critical |
| `db_recovered` | The probe succeeded after a previous outage | Recovery |
| `scheduler_task_crashed` | A scheduler handler raised an unhandled exception | Critical |
| `background_loop_crashed` | A supervised background loop (`stats_collection`, `library_cache`, `health_monitor`, …) crashed and is being restarted | Critical |
| `backup_failed` | `pg_dump` returned a non-zero exit code while building an automatic backup | Warning |
| `pool_saturated` | The async DB connection pool stayed at full capacity for two consecutive checks (~10 minutes) | Warning |

Out of scope on purpose:

- Out-of-memory kills — the kernel terminates the process and Docker
  restarts it; an alert sent from inside a dying process is unreliable.
- Login failures, intrusion attempts and other security events — these
  belong to the security pipeline, not the runtime monitor.
- Business-level events (new request, new media, new ticket) — those
  already use the configurable Discord channel exposed in the admin UI.

---

## 2. Enable the webhook

1. Create an incoming webhook on the destination service (Discord is the
   default target; the embed payload is also accepted by Slack and
   Mattermost via their Discord-compatible adapters).
2. Set `MK_DISCORD_ALERT_WEBHOOK` in your environment file to the
   webhook URL. An empty value disables the feature.
3. Restart the container (or `docker compose up -d` to apply the new
   environment).

`docker-compose.override.example.yml` ships a commented example next to
`BACKUP_PATH`. `.env.example` lists the variable in the optional
section.

The variable is read on every send, so rotating the URL only requires
updating the environment and waiting for the next event — no restart
needed for the new value to apply.

> ⚠️ The webhook URL is a secret. Treat it as you would an API token:
> never commit it to the repository, never paste it in screenshots and
> never include it in support tickets. Rotate it if it leaks.

---

## 3. Payload format

Each alert is delivered as a Discord embed:

- `title` — human label of the category (e.g. `Database unavailable`).
- `color` — semantic color: red for critical, yellow for warning, green
  for recovery.
- `timestamp` — ISO-8601 UTC at the moment the alert was emitted.
- `fields` — small bag of context: app version, plus a few caller-
  provided keys (task name, error excerpt, `consecutive_failures`,
  `checked_out`, …). Values longer than 1 KB are truncated.

The payload never contains DB credentials, webhook URLs, request
bodies or anything else that would be unsafe to publish in a chat
channel. Error strings are clipped to 200 characters.

---

## 4. Debounce

Each category has a 30-minute debounce window backed by an in-memory
dictionary. Two events of the same category inside the window collapse
into a single delivery; events of different categories are independent.

The state is per-process and lost on restart. This is intentional:

- A container restart is itself a strong operational signal.
- The typical container uptime exceeds the debounce window, so the
  trade-off is acceptable.
- Avoiding persistent storage keeps the alert path completely
  independent of the database — which is what makes it possible to
  alert on database outages.

If you need to test the chain repeatedly, restart the container between
tries to clear the debounce state.

---

## 5. Troubleshooting

### No alert arrives during a known incident

1. Confirm `MK_DISCORD_ALERT_WEBHOOK` is set and not empty inside the
   container: `docker compose exec mediakeeper printenv MK_DISCORD_ALERT_WEBHOOK`
   should print the URL.
2. Check the debounce window: an earlier alert of the same category in
   the last 30 minutes will suppress the new one. Restart the container
   to clear state for an end-to-end test.
3. Look for `mediakeeper.monitoring` lines in the application log. A
   delivery failure is logged as a warning.
4. Verify the destination accepts the payload. Some receivers reject
   embed-only messages; switch to a Discord-compatible endpoint.

### The webhook is being spammed

The debounce should make this almost impossible. If you see more than
one alert per category per 30 minutes:

1. Check whether multiple containers share the same webhook URL — each
   container has its own debounce state.
2. Confirm the container did not restart between alerts.
3. Inspect the log for repeated `[health_monitor]` warnings; an
   intermittent DB issue can legitimately fire `db_unavailable` then
   `db_recovered` repeatedly.

### The webhook URL is down

A 5-second HTTP timeout is enforced and the response is captured
silently — no retry, no second alert about the failed alert. The event
is dropped from the operator's point of view, but the consecutive
counters keep running so a still-broken DB will eventually retry on the
next cycle.

---

## 6. Smoke test

There is no built-in test endpoint (the webhook is purposely sealed
inside the runtime layer to avoid an authenticated path that would let
an attacker probe arbitrary URLs). The simplest end-to-end check is:

1. Set `MK_DISCORD_ALERT_WEBHOOK` to a webhook you own.
2. Stop the database container while the application is running.
3. Within ~10 minutes (`HEALTH_MONITOR_INTERVAL_SEC` × `HEALTH_MONITOR_FAILURES_BEFORE_ALERT`)
   a `Database unavailable` alert lands in the channel.
4. Start the database again. A `Database recovered` alert lands within
   five minutes.

If you do not see either alert, follow the troubleshooting checklist
above.

---

## See also

- [`backup-restore.md`](backup-restore.md) — operator restore runbook.
- [`runbook-incidents.md`](runbook-incidents.md) — incident response
  playbooks; the alert categories above map onto its decision tree.
