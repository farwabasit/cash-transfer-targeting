"""Create the RSA key pair for the Snowflake service user.

Writes the PRIVATE key to .secrets/snowflake_key.p8 (git-ignored, never share it)
and prints the PUBLIC key to paste into snowflake/00_setup.sql.
"""
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

ROOT = Path(__file__).resolve().parents[1]
out = ROOT / ".secrets" / "snowflake_key.p8"

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
print("Public key (paste between the quotes in snowflake/00_setup.sql):\n")
print(body)
