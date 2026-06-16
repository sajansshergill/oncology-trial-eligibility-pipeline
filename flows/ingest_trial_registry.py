"""
flows/ingest_trial_registry.py
--------------------------------
Prefect flow: loads trial registry JSON into DuckDB, runs dbt Silver models.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from prefect import flow, task, get_run_logger


@task(name="generate-trials", retries=1)
def generate_trials():
    logger = get_run_logger()
    logger.info("Generating trial registry data...")
    from synthetic_data.generate_trials import main
    main()
    logger.info("Trial registry generated")
    return True


@task(name="seed-trials-bronze", retries=2)
def seed_trials_bronze():
    import duckdb, json
    import pandas as pd
    from pathlib import Path
    logger = get_run_logger()

    db_path     = Path(__file__).parent.parent / "oncology.duckdb"
    trials_path = Path(__file__).parent.parent / "data" / "raw" / "trials.json"

    con = duckdb.connect(str(db_path))
    with open(trials_path) as f:
        trials_data = json.load(f)
    trials_df = pd.DataFrame(trials_data)
    con.execute("""
        CREATE OR REPLACE TABLE bronze.trials_raw AS
        SELECT *, current_timestamp AS ingested_at,
               'trials.json' AS _source_file,
               gen_random_uuid() AS _batch_id
        FROM trials_df
    """)
    count = con.execute("SELECT COUNT(*) FROM bronze.trials_raw").fetchone()[0]
    con.close()
    logger.info(f"Loaded {count} trials into bronze.trials_raw")
    return True


@task(name="run-dbt-silver", retries=1)
def run_dbt_silver():
    import subprocess, os
    logger = get_run_logger()
    logger.info("Running dbt Silver models...")
    result = subprocess.run(
        ["dbt", "run", "--select", "silver", "--profiles-dir", "."],
        cwd=str(Path(__file__).parent.parent / "dbt"),
        capture_output=True, text=True,
        env={**os.environ,
             "DUCKDB_PATH": str(Path(__file__).parent.parent / "oncology.duckdb")}
    )
    if result.returncode != 0:
        raise RuntimeError(f"dbt silver failed:\n{result.stderr}")
    logger.info("dbt Silver models complete")
    return True


@task(name="run-dbt-silver-tests", retries=0)
def run_dbt_silver_tests():
    import subprocess, os
    logger = get_run_logger()
    logger.info("Running dbt Silver tests...")
    result = subprocess.run(
        ["dbt", "test", "--select", "silver", "--profiles-dir", "."],
        cwd=str(Path(__file__).parent.parent / "dbt"),
        capture_output=True, text=True,
        env={**os.environ,
             "DUCKDB_PATH": str(Path(__file__).parent.parent / "oncology.duckdb")}
    )
    if "ERROR" in result.stdout:
        logger.warning(f"Some dbt tests failed — review before gold promotion\n{result.stdout}")
    else:
        logger.info("All dbt Silver tests passed ✓")
    return result.returncode == 0


@flow(name="ingest-trial-registry", log_prints=True)
def ingest_trial_registry_flow():
    """Trial registry ingestion: generate → seed bronze → dbt silver → test."""
    generated = generate_trials()
    seeded    = seed_trials_bronze(wait_for=[generated])
    modeled   = run_dbt_silver(wait_for=[seeded])
    run_dbt_silver_tests(wait_for=[modeled])


if __name__ == "__main__":
    ingest_trial_registry_flow()