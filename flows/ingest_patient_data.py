"""
flows/ingest_patient_data.py
-----------------------------
Prefect flow: generates synthetic patient data and seeds DuckDB Bronze layer.
In production this would read from S3 / upstream EHR source.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from prefect import flow, task, get_run_logger


@task(name="generate-synthetic-patients", retries=1)
def generate_patients(n: int = 1000):
    logger = get_run_logger()
    logger.info(f"Generating {n} synthetic patients...")
    from synthetic_data.generate_patients import main
    datasets = main(n)
    logger.info(f"Generated {len(datasets['patients'])} patients, "
                f"{len(datasets['labs'])} lab records")
    return True


@task(name="seed-bronze-layer", retries=2)
def seed_bronze():
    logger = get_run_logger()
    logger.info("Seeding DuckDB Bronze layer...")
    from synthetic_data.seed_local import main
    main()
    logger.info("Bronze layer seeded successfully")
    return True


@task(name="run-dbt-bronze", retries=1)
def run_dbt_bronze():
    import subprocess, os
    logger = get_run_logger()
    logger.info("Running dbt Bronze models...")
    result = subprocess.run(
        ["dbt", "run", "--select", "bronze", "--profiles-dir", "."],
        cwd=str(Path(__file__).parent.parent / "dbt"),
        capture_output=True, text=True,
        env={**os.environ,
             "DUCKDB_PATH": str(Path(__file__).parent.parent / "oncology.duckdb")}
    )
    if result.returncode != 0:
        raise RuntimeError(f"dbt bronze failed:\n{result.stderr}")
    logger.info("dbt Bronze models complete")
    return True


@flow(name="ingest-patient-data", log_prints=True)
def ingest_patient_data_flow(n_patients: int = 1000):
    """Full patient data ingestion: generate → seed → dbt bronze."""
    generated = generate_patients(n_patients)
    seeded    = seed_bronze(wait_for=[generated])
    run_dbt_bronze(wait_for=[seeded])


if __name__ == "__main__":
    ingest_patient_data_flow(n_patients=1000)