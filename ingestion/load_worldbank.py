"""Loads price data from the World Bank API into Snowflake RAW.WORLDBANK_INDICATORS.

Indicators (all countries in the project, 2005 onwards):
  PA.NUS.PRVT.PP  PPP conversion factor, private consumption (local currency per international $)
  PA.NUS.FCRF     official exchange rate (local currency per US $)
  FP.CPI.TOTL     consumer price index (2010 = 100)

The API is sometimes slow or down. Every call has a timeout and is retried with a growing wait.
Rows are merged on (country, indicator, year): new years are added and revised values updated.

    python ingestion/load_worldbank.py --dry-run
    python ingestion/load_worldbank.py
"""
import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ingestion"))
import load_raw  # noqa: E402

COUNTRIES = ["KEN", "UGA", "ETH", "GHA", "HND", "IND", "PAK", "PER"]
INDICATORS = ["PA.NUS.PRVT.PP", "PA.NUS.FCRF", "FP.CPI.TOTL"]
YEARS = "2005:2025"
API = "https://api.worldbank.org/v2/country/{countries}/indicator/{indicator}?date={years}&format=json&per_page=1000&page={page}"
TABLE = "WORLDBANK_INDICATORS"


def get_json(url, tries=5, timeout=90):
    """GET with a timeout. retries on timeouts, 5xx and non-json answers (the api returns html when it's down)"""
    wait = 5
    for attempt in range(1, tries + 1):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ConnectionError) as e:
            if attempt == tries:
                raise RuntimeError(f"World Bank API failed after {tries} tries: {e}") from e
            print(f"  try {attempt} failed ({type(e).__name__}), waiting {wait}s")
            time.sleep(wait)
            wait *= 2


def fetch(indicator):
    # one country per call: the api is much more reliable with small requests
    rows = []
    for country in COUNTRIES:
        page = 1
        while True:
            meta, *data = get_json(API.format(countries=country, indicator=indicator, years=YEARS, page=page))
            for x in (data[0] if data else []) or []:
                rows.append(dict(COUNTRY=x["countryiso3code"], INDICATOR=indicator, INDICATOR_NAME=x["indicator"]["value"],
                                 YEAR=int(x["date"]), VALUE=x["value"], LAST_UPDATED=meta.get("lastupdated")))
            if page >= int(meta.get("pages", 1)):
                break
            page += 1
    return rows


def merge(conn, df):
    from snowflake.connector.pandas_tools import write_pandas
    cur = conn.cursor()
    cur.execute(f"""create table if not exists RAW.{TABLE} (
        COUNTRY varchar, INDICATOR varchar, INDICATOR_NAME varchar, YEAR number, VALUE float,
        LAST_UPDATED varchar, _LOADED_AT timestamp_ntz)""")
    cur.execute(f"create or replace temporary table RAW.{TABLE}_STAGE like RAW.{TABLE}")
    write_pandas(conn, df, f"{TABLE}_STAGE", schema="RAW", quote_identifiers=True, use_logical_type=True)
    cur.execute(f"""
        merge into RAW.{TABLE} t using RAW.{TABLE}_STAGE s
          on t.COUNTRY = s.COUNTRY and t.INDICATOR = s.INDICATOR and t.YEAR = s.YEAR
        when matched and (t.VALUE is distinct from s.VALUE) then update set
          VALUE = s.VALUE, INDICATOR_NAME = s.INDICATOR_NAME, LAST_UPDATED = s.LAST_UPDATED, _LOADED_AT = s._LOADED_AT
        when not matched then insert (COUNTRY, INDICATOR, INDICATOR_NAME, YEAR, VALUE, LAST_UPDATED, _LOADED_AT)
          values (s.COUNTRY, s.INDICATOR, s.INDICATOR_NAME, s.YEAR, s.VALUE, s.LAST_UPDATED, s._LOADED_AT)""")
    inserted, updated = cur.fetchone()[:2]
    return inserted, updated


def main():
    ap = argparse.ArgumentParser(description="Load World Bank price data into Snowflake")
    ap.add_argument("--dry-run", action="store_true", help="only call the API, don't connect to Snowflake")
    args = ap.parse_args()

    conn = None
    if not args.dry_run:
        load_raw.load_dotenv(ROOT / ".env")
        conn = load_raw.connect()
    try:
        # save after each indicator: a slow api halfway then doesn't lose what already came in
        for ind in INDICATORS:
            got = fetch(ind)
            df = pd.DataFrame(got).dropna(subset=["VALUE"])
            df["_LOADED_AT"] = datetime.now(timezone.utc).replace(tzinfo=None)
            if conn is None:
                print(f"{ind}: {len(df)} values, years {df.YEAR.min()}-{df.YEAR.max()}")
                continue
            inserted, updated = merge(conn, df)
            print(f"{ind}: {len(df)} values -> RAW.{TABLE}: {inserted} new, {updated} updated", flush=True)
    finally:
        if conn is not None:
            conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
