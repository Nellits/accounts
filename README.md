# Accounts

Shared identity service for sibling apps. Hosted at whatever domain you configure (today: `accounts.nellits.com`).

One login on the web (session cookie on the parent domain). Mobile apps use `POST /api/auth/token` and send `Authorization: Bearer …`.

## Layout

| Path | Purpose |
|------|---------|
| `service/` | FastAPI identity API (RS256 JWT, JWKS, users, avatars) |
| `frontend/` | Hosted login / register / reset UI |
| `packages/auth/` | Python FastAPI dependency for app backends |
| `packages/auth-js/` | TypeScript helpers for app frontends |
| `docs/DEPLOY.md` | Railway + DNS + user migration |

## Quick local start

```bash
# 1) Keys (optional locally — ephemeral key is generated if unset)
python service/scripts/generate_keys.py

# 2) Database
docker compose up -d db
cp service/.env.example service/.env
# edit DATABASE_URL if needed

cd service && pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8001

# 3) Login UI (dev)
cd frontend && npm install && npm run dev
# open http://localhost:5175/login
```

JWKS: `http://localhost:8001/.well-known/jwks.json`

## App integration

Backend:

```python
from auth import CurrentUserId
```

```bash
pip install "auth @ git+https://github.com/Nellits/accounts.git@main#subdirectory=packages/auth"
```

Env on each app:

```
AUTH_ISSUER_URL=https://accounts.nellits.com
AUTH_JWKS_URL=https://accounts.nellits.com/.well-known/jwks.json
AUTH_COOKIE_NAME=accounts_session
```

Frontend: set `VITE_ACCOUNTS_URL` and use the `auth` package helpers (`getMe`, `redirectToLogin`, `logout`).
