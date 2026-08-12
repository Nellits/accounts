# Deploy Nellits Accounts (Railway)

## Status

Railway project **nellits-accounts** / service **accounts** is deployed. Health checks succeed inside the container (`{"ok":true}`).

## 1. DNS (required for public URL + SSO cookies)

Add this CNAME at your DNS provider for `nellits.com`:

| Host | Type | Value |
|------|------|-------|
| `accounts` | CNAME | `9qdt7krf.up.railway.app` |

Confirm the target anytime with `cd nellits-accounts && railway domain`.

Until DNS propagates, `https://accounts.nellits.com` will not resolve. Cookie SSO (`Domain=.nellits.com`) only works over HTTPS on that host.

## 2. Database

Postgres is provisioned in the same Railway project. Schema migrates on each start via `service/start.sh` (`alembic upgrade head`).

## 3. Signing keys

RSA keys are stored in Railway env as `AUTH_RSA_PRIVATE_KEY` / `AUTH_RSA_PUBLIC_KEY` (`AUTH_KEY_ID=nellits-1`).

Rotate by regenerating with `python service/scripts/generate_keys.py` and updating those variables (invalidates all sessions).

## 4. Other env (already set on Railway)

| Variable | Value |
|----------|-------|
| `AUTH_ISSUER` | `https://accounts.nellits.com` |
| `AUTH_COOKIE_DOMAIN` | `.nellits.com` |
| `AUTH_COOKIE_SECURE` | `true` |
| `PASSWORD_RESET_FRONTEND_URL` | `https://accounts.nellits.com` |
| `ACCOUNTS_UPLOADS_DIR` | `/data/uploads` (volume at `/data`) |
| `CORS_ORIGINS` | includes `https://tv.nellits.com` |

## 5. Migrate users from TV Tracker (preserve IDs)

```bash
cd service
export DATABASE_URL=...              # accounts
export TVTRACKER_DATABASE_URL=...    # tvtracker Postgres
export ADMIN_USER_IDS=1
python scripts/migrate_from_tvtracker.py --dry-run
python scripts/migrate_from_tvtracker.py
```

Copy avatar files from tvtracker's uploads volume into accounts `/data/uploads/avatars/` if desired.

## 6. Point apps at accounts

```
AUTH_ISSUER_URL=https://accounts.nellits.com
AUTH_JWKS_URL=https://accounts.nellits.com/.well-known/jwks.json
AUTH_COOKIE_NAME=nellits_session
VITE_ACCOUNTS_URL=https://accounts.nellits.com
```
