# Nellits Auth (Python)

FastAPI dependency that validates JWTs issued by **Nellits Accounts** using JWKS.

## Install

```bash
pip install "nellits-auth @ git+https://github.com/YOUR_ORG/nellits-accounts.git#subdirectory=packages/nellits_auth"
# or local editable:
pip install -e ../nellits-accounts/packages/nellits_auth
```

## Env

- `AUTH_ISSUER_URL` — e.g. `https://accounts.nellits.com`
- `AUTH_JWKS_URL` — optional; defaults to `{AUTH_ISSUER_URL}/.well-known/jwks.json`
- `AUTH_COOKIE_NAME` — default `nellits_session`

## Usage

```python
from nellits_auth import CurrentUserId, CurrentUser, require_admin

@router.get("/items")
def list_items(user_id: CurrentUserId):
    ...

@router.get("/admin")
def admin(user: CurrentUser, _: None = Depends(require_admin)):
    ...
```
