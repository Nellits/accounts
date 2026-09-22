# Deploy Accounts (Railway)

## Status

Railway project **nellits** currently hosts every app. Accounts runs as service **accounts** with its own
Postgres (**accounts-db**) and a volume mounted at `/data`. Health checks pass (`{"ok":true}`) and
`/.well-known/jwks.json` serves the signing key (`AUTH_KEY_ID`, default `accounts-1`).

Project layout:

| Service | Purpose |
|---------|---------|
| `accounts` | This service (identity for all apps) |
| `accounts-db` | Postgres for accounts |
| `tvtracker` | TV Tracker app |
| `tvtracker-db` | Postgres for TV Tracker |

Railway cannot move a service between projects, so new apps should be created **inside** the shared
project rather than in a project of their own.

## 1. DNS (required for public URL + SSO cookies)

Add this CNAME at your DNS provider (current apex: `nellits.com`):

| Host | Type | Value |
|------|------|-------|
| `accounts` | CNAME | `k9vwvr8e.up.railway.app` |

Confirm the target anytime with `railway domain --service accounts`.

Until DNS propagates, `https://accounts.nellits.com` will not resolve. Cookie SSO
(`AUTH_COOKIE_DOMAIN=.nellits.com`) only works over HTTPS on that host. The service is reachable
meanwhile at its Railway domain.

## 2. Database

`DATABASE_URL` is a Railway reference to `${{accounts-db.DATABASE_URL}}`, so it follows the database
service rather than a hardcoded host. Schema migrates on each start via `backend/start.sh`
(`alembic upgrade head`).

Note: these references bind to a service **id**. If you ever delete and recreate `accounts-db`, re-set
`DATABASE_URL` — recreating with the same name does not relink it.

## 3. Signing keys

RSA keys live in Railway env as `AUTH_RSA_PRIVATE_KEY` / `AUTH_RSA_PUBLIC_KEY` (`AUTH_KEY_ID=accounts-1`).
PEM newlines may be stored escaped as `\n`; the service converts them on load.

Rotate by regenerating with `python backend/scripts/generate_keys.py` and updating those variables.
Rotating invalidates every existing session.

## 4. Environment (set on the `accounts` service)

| Variable | Value |
|----------|-------|
| `AUTH_ISSUER` | `https://accounts.nellits.com` |
| `AUTH_COOKIE_NAME` | `accounts_session` |
| `AUTH_COOKIE_DOMAIN` | `.nellits.com` |
| `AUTH_COOKIE_SECURE` | `true` |
| `AUTH_KEY_ID` | `accounts-1` |
| `ACCESS_TOKEN_EXPIRE_DAYS` | `30` |
| `CORS_ORIGINS` | includes `https://tv.nellits.com` |
| `PASSWORD_RESET_FRONTEND_URL` | `https://accounts.nellits.com` |
| `EMAIL_FROM` | `noreply@nellits.com` |
| `APP_NAME` | `Accounts` |
| `ACCOUNTS_UPLOADS_DIR` | `/data/uploads` (volume at `/data`) |
| `DATABASE_URL` | `${{accounts-db.DATABASE_URL}}` |
| `TVTRACKER_DATABASE_URL` | `${{tvtracker-db.DATABASE_URL}}` (migration only) |
| `ADMIN_USER_IDS` | `1` (migration only; marks `is_admin`) |

`RESEND_API_KEY` is not set yet, so password-reset emails are logged rather than sent.

Redirects after login are allowed for hosts under `AUTH_COOKIE_DOMAIN` (plus localhost and any
prefixes in `AUTH_REDIRECT_ALLOWLIST`).

## 5. Migrate users from TV Tracker (preserve IDs)

Both databases are in the same project, so this runs on the private network from inside the container:

```bash
railway ssh --service accounts
python scripts/migrate_from_tvtracker.py --dry-run
python scripts/migrate_from_tvtracker.py
```

IDs are preserved so TV Tracker's existing rows keep pointing at the right people. Copy avatar files
from TV Tracker's uploads volume into `/data/uploads/avatars/` if you want them to carry over.

## 6. Point apps at accounts

```
AUTH_ISSUER_URL=https://accounts.nellits.com
AUTH_JWKS_URL=https://accounts.nellits.com/.well-known/jwks.json
AUTH_COOKIE_NAME=accounts_session
VITE_ACCOUNTS_URL=https://accounts.nellits.com
```
