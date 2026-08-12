"""Generate RSA key pair for RS256 JWT signing.

Usage:
  python scripts/generate_keys.py
  # writes keys/private.pem and keys/public.pem under repo root
"""
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

ROOT = Path(__file__).resolve().parents[2]
KEYS = ROOT / "keys"
KEYS.mkdir(parents=True, exist_ok=True)

private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
public_key = private_key.public_key()

priv_path = KEYS / "private.pem"
pub_path = KEYS / "public.pem"

priv_path.write_bytes(
    private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
)
pub_path.write_bytes(
    public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
)

print(f"Wrote {priv_path}")
print(f"Wrote {pub_path}")
print("Set AUTH_RSA_PRIVATE_KEY_PATH / AUTH_RSA_PUBLIC_KEY_PATH (or paste PEMs into env).")
