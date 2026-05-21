# Recovering admin access

This guide covers the case where the backoffice admin account is locked out and you can no longer sign in: the bootstrap password printed on first boot was missed, the new password chosen on first login was forgotten, or the account was disabled by mistake. It targets self-hosters running the published image (`ghcr.io/keeperd93/mediakeeper`).

> [!IMPORTANT]
> The initial admin password is printed **once** on `stdout` during the first container boot and is never persisted anywhere on the volume. Capture it immediately. If you missed it, follow the procedure below — it works at any time, not just on first boot.

## Reset the admin password from the host

The container ships with a CLI helper that re-randomises the admin password, forces a password change on next login, and invalidates every existing session. Run it from the host with `docker exec`:

```sh
docker exec -w /app/backend mediakeeper \
    python -m scripts.reset_admin --username admin
```

The new credentials are printed once on the command's `stdout`, in the same banner format as the first-boot bootstrap message:

```
============================================================
  ADMIN PASSWORD RESET
  Username: admin
  Password: <fresh-random-token>
  You MUST change this password on next login.
  Existing sessions have been invalidated.
============================================================
```

Copy the password immediately — it is never written to a file and is gone from the buffer as soon as you close the terminal.

> [!NOTE]
> The container name is `mediakeeper` if you started it through `docker-compose.prod.yml` as shipped. Replace it with whatever you set under `container_name:` if you customised the compose file.

## Exit codes

| Code | Meaning                                                                                          |
| ---- | ------------------------------------------------------------------------------------------------ |
| `0`  | Reset succeeded. The new password is on `stdout`.                                                |
| `1`  | The named user does not exist. Check the spelling or list users via `psql`.                      |
| `2`  | The named user exists but is not on the backoffice allow-list. Use the portal admin tools.       |

The script writes to `stderr` on the non-zero paths so a wrapper script can distinguish "no such user" from "wrong account type".

## After the reset

1. Open the web UI and sign in as the admin with the freshly printed password.
2. The "you must change your password" screen is forced — pick a new strong password (the same complexity rules as a first-boot reset apply: 12+ characters, mix of cases, digits, special characters, 12+ distinct characters).
3. The previous JWT cookies from any active browser session are invalidated by the `tokens_invalidated_at` stamp the script writes — every other tab is logged out automatically on its next API call.

## Reset a different admin account

`--username` defaults to `admin`. If you renamed the bootstrap account or you operate several admins, pass the actual username:

```sh
docker exec -w /app/backend mediakeeper \
    python -m scripts.reset_admin --username keeper-ops
```

The script refuses to reset a portal-only account (exit code `2`). Use the regular **Users** admin page for those.

## Why no persistent password file?

A persistent recovery file under `/data/` would survive backups, volume inspection and `docker cp` — anyone who can read the volume could read the admin password. The CLI route keeps the secret in flight only: it is generated, printed, hashed into the database, and the local copy is forgotten. The trade-off is that you need shell access to the host to recover, which is an acceptable bar for a self-hosted deployment.
