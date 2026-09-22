# Nellits Accounts

Shared identity service for all Nellits apps (`accounts.nellits.com`). Repo: [Nellits/accounts](https://github.com/Nellits/accounts).

One login on the web (session cookie on `.nellits.com`). Mobile apps use `POST /api/auth/token` and send `Authorization: Bearer …`.

## Layout

| Path | Purpose |
|------|---------|
| `service/` | FastAPI identity API (RS256 JWT, JWKS, users, avatars) |
| `frontend/` | Hosted login / register / reset UI |
| `packages/nellits_auth/` | Python FastAPI dependency for app backends |
| `packages/nellits-auth-js/` | TypeScript helpers for app frontends |
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
from nellits_auth import CurrentUserId
```

Env on each app:

```
AUTH_ISSUER_URL=https://accounts.nellits.com
AUTH_JWKS_URL=https://accounts.nellits.com/.well-known/jwks.json
```

Frontend: set `VITE_ACCOUNTS_URL` and use `@nellits/auth` helpers (`getMe`, `redirectToLogin`, `logout`).
