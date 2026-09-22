# Auth (Python)

FastAPI dependency that validates JWTs issued by **Accounts** using JWKS.

## Install

```bash
pip install "auth @ git+https://github.com/Nellits/accounts.git@main#subdirectory=packages/auth"
# or locally:
pip install -e ../accounts/packages/auth
```

## Env

- `AUTH_ISSUER_URL` — e.g. `https://accounts.example.com`
- `AUTH_JWKS_URL` — defaults to `{issuer}/.well-known/jwks.json`
- `AUTH_COOKIE_NAME` — default `accounts_session`

## Usage

```python
from auth import CurrentUserId, CurrentUser, require_admin
```
