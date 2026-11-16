"""Create an RSA key pair for a Snowflake service user.

    python ingestion/make_keypair.py              -> .secrets/snowflake_key.p8 (pipeline)
    python ingestion/make_keypair.py app_key      -> .secrets/app_key.p8 (read-only app user)

The private key stays in .secrets/ (git-ignored). The public key is printed to paste into Snowflake.
"""
import sys
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

ROOT = Path(__file__).resolve().parents[1]
name = sys.argv[1] if len(sys.argv) > 1 else "snowflake_key"
out = ROOT / ".secrets" / f"{name}.p8"

if out.exists():
    raise SystemExit(f"{out} already exists; delete it first if you really want a new key.")

key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
out.parent.mkdir(exist_ok=True)
out.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                  serialization.NoEncryption()))
pub = key.public_key().public_bytes(serialization.Encoding.PEM,
                                    serialization.PublicFormat.SubjectPublicKeyInfo).decode()
body = "".join(l for l in pub.splitlines() if "-----" not in l)
print(f"Private key saved to {out}\n")
print("Public key:\n")
print(body)
