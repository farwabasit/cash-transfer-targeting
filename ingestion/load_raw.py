"""Land raw survey files in Snowflake RAW, incrementally.

- Each file is loaded once: its SHA-256 hash is recorded in RAW._LOAD_LOG and skipped next time.
- Schema drift: columns that appear in a new file are added to the existing table;
  columns missing from a new file are left NULL.
- Every row gets lineage columns: _DATASET, _WAVE, _SOURCE_FILE, _FILE_HASH, _LOADED_AT.

Usage:
    python ingestion/load_raw.py --dry-run     # read files and show the plan, no Snowflake
    python ingestion/load_raw.py               # load new files
    python ingestion/load_raw.py --force       # reload everything (replaces earlier rows of the same file)
"""
import argparse
import hashlib
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "RAW"
LOG_TABLE = "_LOAD_LOG"


def load_dotenv(path: Path) -> None:
    """Minimal .env reader so local runs need no extra package (Docker uses --env-file)."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_file(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".dta":
        # keep numeric codes; value labels are documented in the questionnaires
        df = pd.read_stata(path, convert_categoricals=False)
    elif path.suffix.lower() == ".csv":
        df = pd.read_csv(path)
    else:
        raise ValueError(f"Unsupported file type: {path.suffix}")
    df.columns = [c.strip().upper() for c in df.columns]
    return df.copy()  # read_stata returns a fragmented frame; copy makes adding columns fast


def snowflake_type(dtype) -> str:
    if pd.api.types.is_bool_dtype(dtype):
        return "BOOLEAN"
    if pd.api.types.is_integer_dtype(dtype):
        return "NUMBER"
    if pd.api.types.is_float_dtype(dtype):
        return "FLOAT"
    if pd.api.types.is_datetime64_any_dtype(dtype):
        return "TIMESTAMP_NTZ"
    return "VARCHAR"


def connect():
    import snowflake.connector
    from cryptography.hazmat.primitives import serialization

    if os.environ.get("SNOWFLAKE_PRIVATE_KEY"):            # CI: key content in a secret
        pem = os.environ["SNOWFLAKE_PRIVATE_KEY"].encode()
    else:                                                  # local / Docker: key file
        key_path = Path(os.environ["SNOWFLAKE_PRIVATE_KEY_PATH"]).expanduser()
        if not key_path.is_absolute():
            key_path = ROOT / key_path
        pem = key_path.read_bytes()
    key = serialization.load_pem_private_key(pem, password=None)
    der = key.private_bytes(serialization.Encoding.DER, serialization.PrivateFormat.PKCS8,
                            serialization.NoEncryption())
    return snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        private_key=der,
        role=os.environ.get("SNOWFLAKE_ROLE"),
        warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE"),
        database=os.environ["SNOWFLAKE_DATABASE"],
        schema=SCHEMA,
    )


def ensure_log_table(cur) -> None:
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS {SCHEMA}.{LOG_TABLE} (
            FILE_HASH VARCHAR, SOURCE_FILE VARCHAR, TARGET_TABLE VARCHAR,
            DATASET VARCHAR, WAVE VARCHAR, ROW_COUNT NUMBER, COLUMN_COUNT NUMBER,
            NEW_COLUMNS VARCHAR, LOADED_AT TIMESTAMP_NTZ)""")


def existing_columns(cur, table: str) -> list[str]:
    cur.execute("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
                "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s", (SCHEMA, table))
    return [r[0] for r in cur.fetchall()]


def load_one(conn, src: dict, df: pd.DataFrame, digest: str, force: bool) -> str:
    from snowflake.connector.pandas_tools import write_pandas

    table = src["table"].upper()
    cur = conn.cursor()
    cur.execute(f"SELECT COUNT(*) FROM {SCHEMA}.{LOG_TABLE} WHERE FILE_HASH = %s AND TARGET_TABLE = %s",
                (digest, table))
    if cur.fetchone()[0] and not force:
        return "skipped (already loaded)"

    cols = existing_columns(cur, table)
    new_cols = []
    if cols:
        if force:
            cur.execute(f'DELETE FROM {SCHEMA}."{table}" WHERE "_FILE_HASH" = %s', (digest,))
            cur.execute(f"DELETE FROM {SCHEMA}.{LOG_TABLE} WHERE FILE_HASH = %s AND TARGET_TABLE = %s",
                        (digest, table))
        new_cols = [c for c in df.columns if c not in cols]
        for c in new_cols:                                  # schema drift: add, don't fail
            cur.execute(f'ALTER TABLE {SCHEMA}."{table}" ADD COLUMN "{c}" {snowflake_type(df[c].dtype)}')

    ok, _, nrows, _ = write_pandas(conn, df, table, schema=SCHEMA, auto_create_table=not cols,
                                   quote_identifiers=True, use_logical_type=True)
    if not ok:
        raise RuntimeError(f"write_pandas failed for {table}")

    cur.execute(f"INSERT INTO {SCHEMA}.{LOG_TABLE} VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (digest, src["path"], table, src["dataset"], src["wave"], nrows, df.shape[1],
                 ",".join(new_cols), datetime.now(timezone.utc).replace(tzinfo=None)))
    drift = f", {len(new_cols)} new columns" if new_cols else ""
    return f"loaded {nrows} rows{drift}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true", help="read files and print the plan only")
    ap.add_argument("--force", action="store_true", help="reload files that were already loaded")
    ap.add_argument("--sources", default=str(ROOT / "ingestion" / "sources.yml"))
    args = ap.parse_args()

    load_dotenv(ROOT / ".env")
    sources = yaml.safe_load(Path(args.sources).read_text(encoding="utf-8"))["sources"]
    loaded_at = datetime.now(timezone.utc).replace(tzinfo=None)

    conn = None if args.dry_run else connect()
    if conn:
        ensure_log_table(conn.cursor())

    for src in sources:
        path = ROOT / src["path"]
        if not path.exists():
            print(f"[missing] {src['path']}")
            continue
        digest = file_hash(path)
        df = read_file(path)
        df = df.assign(_DATASET=src["dataset"], _WAVE=src["wave"], _SOURCE_FILE=path.name,
                       _FILE_HASH=digest, _LOADED_AT=loaded_at).copy()
        if args.dry_run:
            print(f"[plan] {src['path']} -> {SCHEMA}.{src['table']}: {df.shape[0]} rows x {df.shape[1]} cols, "
                  f"hash {digest[:12]}")
            continue
        print(f"[{src['table']}] {load_one(conn, src, df, digest, args.force)}")

    if conn:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
