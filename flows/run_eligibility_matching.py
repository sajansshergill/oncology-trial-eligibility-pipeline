"""
flows/run_eligibility_matching.py
-----------------------------------
Prefect flow: parses trial criteria via Claude API, runs patient×trial
matching, writes results to gold layer, runs dbt Gold models.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from prefect import flow, task, get_run_logger


@task(name="run-eligibility-engine", retries=1)
def run_eligibility_engine(limit_patients: int = None):
    logger = get_run_logger()
    logger.info("Starting eligibility matching engine...")
    from eligibility.engine import run_matching
    results = run_matching(limit_patients=limit_patients)
    logger.info(f"Matching complete — {len(results)} patient×trial pairs evaluated")
    return len(results)


@task(name="run-dbt-gold", retries=1)
def run_dbt_gold():
    import subprocess, os
    logger = get_run_logger()
    logger.info("Running dbt Gold models...")
    result = subprocess.run(
        ["dbt", "run", "--select", "gold", "--profiles-dir", "."],
        cwd=str(Path(__file__).parent.parent / "dbt"),
        capture_output=True, text=True,
        env={**os.environ,
             "DUCKDB_PATH": str(Path(__file__).parent.parent / "oncology.duckdb")}
    )
    if result.returncode != 0:
        raise RuntimeError(f"dbt gold failed:\n{result.stderr}")
    logger.info("dbt Gold models complete")
    return True


@task(name="log-match-summary")
def log_match_summary():
    import duckdb
    logger = get_run_logger()
    db_path = Path(__file__).parent.parent / "oncology.duckdb"
    con = duckdb.connect(str(db_path))
    try:
        summary = con.execute("""
            SELECT nct_id, primary_indication, phase,
                   patients_evaluated, fully_eligible_count,
                   eligibility_rate_pct, avg_match_score
            FROM main_gold.mart_cohort_summary
            ORDER BY fully_eligible_count DESC
        """).df()
        logger.info(f"\nMatch Summary:\n{summary.to_string(index=False)}")
    except Exception as e:
        logger.warning(f"Could not load summary: {e}")
    finally:
        con.close()


@flow(name="run-eligibility-matching", log_prints=True)
def run_eligibility_matching_flow(limit_patients: int = None):
    """Full matching pipeline: engine → dbt gold → summary."""
    n_evaluated = run_eligibility_engine(limit_patients=limit_patients)
    dbt_done    = run_dbt_gold(wait_for=[n_evaluated])
    log_match_summary(wait_for=[dbt_done])


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    run_eligibility_matching_flow(limit_patients=args.limit)