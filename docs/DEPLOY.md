# Deploy Nellits Accounts (Railway)

## 1. DNS

Add a CNAME (or Railway custom domain) for **`accounts.nellits.com`** → your Railway accounts service.

Cookie SSO requires apps on the same parent domain (`tv.nellits.com`, `todos.nellits.com`, …) and:

```
AUTH_COOKIE_DOMAIN=.nellits.com
AUTH_COOKIE_SECURE=true
AUTH_ISSUER=https://accounts.nellits.com
```

## 2. Database

Provision Postgres (new Railway Postgres, or a second database on an existing instance). Set `DATABASE_URL`.

Pre-deploy: `alembic upgrade head` (run from `service/`).

## 3. Signing keys

Generate once and store as env (or mount files):

```bash
python service/scripts/generate_keys.py
```

Set either:

- `AUTH_RSA_PRIVATE_KEY` / `AUTH_RSA_PUBLIC_KEY` (PEM with `\n` escapes), or
- `AUTH_RSA_PRIVATE_KEY_PATH` / `AUTH_RSA_PUBLIC_KEY_PATH`

Also set `AUTH_KEY_ID=nellits-1` (must match JWKS `kid`).

## 4. Other env

| Variable | Example |
|----------|---------|
| `PASSWORD_RESET_FRONTEND_URL` | `https://accounts.nellits.com` |
| `RESEND_API_KEY` / `EMAIL_FROM` | email delivery |
| `CORS_ORIGINS` | `https://tv.nellits.com,https://todos.nellits.com` |
| `ACCOUNTS_UPLOADS_DIR` | `/data/uploads` (attach a Railway volume at `/data`) |
| `FRONTEND_DIST` | set by Dockerfile |

## 5. Migrate users from TV Tracker (preserve IDs)

After accounts schema is migrated:

```bash
cd service
export DATABASE_URL=...          # accounts DB
export TVTRACKER_DATABASE_URL=... # tvtracker DB
export ADMIN_USER_IDS=1          # optional
python scripts/migrate_from_tvtracker.py --dry-run
python scripts/migrate_from_tvtracker.py
```

Copy avatar files from tvtracker's uploads volume into accounts `/data/uploads/avatars/` if you want existing avatars to keep working.

Existing HS256 session cookies on `tv.nellits.com` will stop working; users sign in once at accounts.

## 6. Point apps at accounts

Each app:

```
AUTH_ISSUER_URL=https://accounts.nellits.com
AUTH_JWKS_URL=https://accounts.nellits.com/.well-known/jwks.json
AUTH_COOKIE_NAME=nellits_session
VITE_ACCOUNTS_URL=https://accounts.nellits.com
```

See TV Tracker migration notes in that repo after cutting over.
