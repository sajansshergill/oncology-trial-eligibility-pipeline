"""
seed_local.py
--------------
Loads all synthetic data files from data/raw/ into DuckDB Bronze layer.
Creates the oncology.duckdb database with bronze schema.

Run after generate_patients.py and generate_trials.py.

Usage:
  python synthetic_data/seed_local.py
"""

import json
from pathlib import Path

import duckdb
import pandas as pd
from datetime import datetime

DB_PATH   = Path(__file__).parent.parent / "oncology.duckdb"
RAW_DIR   = Path(__file__).parent.parent / "data" / "raw"


def seed_bronze(con: duckdb.DuckDBPyConnection):
    con.execute("CREATE SCHEMA IF NOT EXISTS bronze")

    tables = {
        "patients":    RAW_DIR / "patients.parquet",
        "diagnoses":   RAW_DIR / "diagnoses.parquet",
        "labs":        RAW_DIR / "labs.parquet",
        "medications": RAW_DIR / "medications.parquet",
        "biomarkers":  RAW_DIR / "biomarkers.parquet",
    }

    for table, path in tables.items():
        if not path.exists():
            print(f"  ⚠️  {path.name} not found — run generate_patients.py first")
            continue
        con.execute(f"""
            CREATE OR REPLACE TABLE bronze.{table}_raw AS
            SELECT
                *,
                current_timestamp AS ingested_at,
                '{path.name}'     AS _source_file,
                gen_random_uuid() AS _batch_id
            FROM read_parquet('{path}')
        """)
        count = con.execute(f"SELECT COUNT(*) FROM bronze.{table}_raw").fetchone()[0]
        print(f"  ✓ bronze.{table}_raw — {count:,} rows")

    # Trials from JSON
    trials_path = RAW_DIR / "trials.json"
    if trials_path.exists():
        with open(trials_path) as f:
            trials_data = json.load(f)
        trials_df = pd.DataFrame(trials_data)
        con.execute("""
            CREATE OR REPLACE TABLE bronze.trials_raw AS
            SELECT
                *,
                current_timestamp AS ingested_at,
                'trials.json'     AS _source_file,
                gen_random_uuid() AS _batch_id
            FROM trials_df
        """)
        count = con.execute("SELECT COUNT(*) FROM bronze.trials_raw").fetchone()[0]
        print(f"  ✓ bronze.trials_raw — {count:,} rows")
    else:
        print("  ⚠️  trials.json not found — run generate_trials.py first")


def print_summary(con: duckdb.DuckDBPyConnection):
    print("\n📊 Bronze layer summary:")
    tables = con.execute("""
        SELECT table_name, estimated_size
        FROM duckdb_tables()
        WHERE schema_name = 'bronze'
        ORDER BY table_name
    """).fetchall()
    for name, size in tables:
        count = con.execute(f"SELECT COUNT(*) FROM bronze.{name}").fetchone()[0]
        print(f"   bronze.{name:<25} {count:>8,} rows")


def main():
    print(f"\n🦆 Seeding DuckDB — {DB_PATH}\n")
    con = duckdb.connect(str(DB_PATH))
    seed_bronze(con)
    print_summary(con)
    con.close()
    print(f"\n✅ Done. Database at {DB_PATH}\n")


if __name__ == "__main__":
    main()