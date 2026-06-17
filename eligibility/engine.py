"""
eligibility/engine.py
---------------------
Core patient × trial matching engine.
Reads from DuckDB Silver layer, evaluates parsed criteria,
writes fact_trial_matches results back to DuckDB Gold layer.
"""

import json
import sys
import os
from datetime import datetime
from pathlib import Path

import duckdb
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from eligibility.models import MatchResult, CriterionResult
from eligibility.parser import parse_criteria
from eligibility.evaluators.lab_evaluator import evaluate_lab
from eligibility.evaluators.biomarker_evaluator import evaluate_biomarker
from eligibility.evaluators.medication_evaluator import evaluate_medication

DB_PATH = Path(__file__).parent.parent / "oncology.duckdb"


# ── Patient data loader ───────────────────────────────────────────────────────

def load_patient_clinical_data(con: duckdb.DuckDBPyConnection, patient_id: str) -> dict:
    """Load all clinical data for a patient into a structured dict."""

    # Most recent lab values per test
    labs_df = con.execute("""
        SELECT lab_name, value, normal_high, normal_low
        FROM main_silver.dim_labs
        WHERE patient_id = ? AND recency_rank = 1
    """, [patient_id]).df()

    labs = {
        row["lab_name"]: {
            "value":       row["value"],
            "normal_high": row["normal_high"],
            "normal_low":  row["normal_low"],
        }
        for _, row in labs_df.iterrows()
    }

    # Biomarkers
    bm = con.execute("""
        SELECT * FROM main_silver.dim_biomarkers WHERE patient_id = ?
    """, [patient_id]).df()

    biomarkers = {}
    if not bm.empty:
        row = bm.iloc[0]
        biomarkers = {
            col: row[col]
            for col in bm.columns
            if col not in ("biomarker_id", "patient_id", "cancer_type",
                           "test_date", "ingested_at", "_source_file", "_batch_id")
            and row[col] is not None
            and str(row[col]).lower() != "unknown"
        }

    # Medication history
    meds_df = con.execute("""
        SELECT drug_name, drug_class, line_of_therapy,
               start_date, end_date, discontinuation_reason,
               is_prior_anthracycline, is_prior_immunotherapy,
               is_prior_egfr_inhibitor, is_prior_cdk46_inhibitor,
               is_prior_osimertinib, is_prior_trastuzumab
        FROM main_silver.dim_medications
        WHERE patient_id = ?
    """, [patient_id]).to_dict(orient="records")

    return {"labs": labs, "biomarkers": biomarkers, "medications": meds_df}


# ── Criterion dispatcher ──────────────────────────────────────────────────────

def evaluate_criterion(criterion: dict, patient_data: dict,
                       patient_row: pd.Series) -> CriterionResult:
    """Route criterion to the appropriate evaluator."""
    ctype = criterion.get("type", "other")
    field = criterion.get("field", "")

    # ECOG
    if ctype == "ecog" or field == "ecog_status":
        actual = int(patient_row.get("ecog_status", 99))
        op     = criterion.get("operator", "lte")
        val    = int(criterion.get("value", 2))
        passed = _compare_numeric(actual, op, val)
        return CriterionResult(
            criterion_id=criterion["criterion_id"],
            passed=passed,
            reason=f"ECOG {actual} {'passes' if passed else 'fails'} {op} {val}",
            actual_value=actual
        )

    # Lab
    if ctype == "lab" or field in patient_data["labs"]:
        return evaluate_lab(criterion, patient_data["labs"])

    # Biomarker
    if ctype == "biomarker" or field in patient_data["biomarkers"]:
        return evaluate_biomarker(criterion, patient_data["biomarkers"])

    # Medication history
    if ctype == "medication_history":
        return evaluate_medication(criterion, patient_data["medications"])

    # Diagnosis / cancer type
    if ctype == "diagnosis" or field in ("primary_cancer", "stage_at_dx", "is_metastatic"):
        actual = str(patient_row.get(field, "")).lower()
        value  = str(criterion.get("value", "")).lower()
        op     = criterion.get("operator", "eq")
        passed = (actual == value) if op == "eq" else (actual != value)
        return CriterionResult(
            criterion_id=criterion["criterion_id"],
            passed=passed,
            reason=f"{field} is '{actual}' — {'matches' if passed else 'fails'} '{value}'",
            actual_value=actual
        )

    # Age
    if ctype == "age" or field == "age_at_diagnosis":
        actual = int(patient_row.get("age_at_diagnosis", 0))
        val    = int(criterion.get("value", 18))
        op     = criterion.get("operator", "gte")
        passed = _compare_numeric(actual, op, val)
        return CriterionResult(
            criterion_id=criterion["criterion_id"],
            passed=passed,
            reason=f"Age {actual} {'passes' if passed else 'fails'} {op} {val}",
            actual_value=actual
        )

    # Fallback
    return CriterionResult(
        criterion_id=criterion["criterion_id"],
        passed=True,
        reason=f"Criterion type '{ctype}' / field '{field}' not evaluable — skipped",
        actual_value=None
    )


def _compare_numeric(actual: float, operator: str, threshold: float) -> bool:
    ops = {"lte": actual <= threshold, "gte": actual >= threshold,
           "lt":  actual <  threshold, "gt":  actual >  threshold,
           "eq":  actual == threshold, "neq": actual != threshold}
    return ops.get(operator, False)


# ── Main engine ───────────────────────────────────────────────────────────────

def evaluate_patient_for_trial(
    patient_row: pd.Series,
    trial_row: pd.Series,
    rules: dict,
    patient_data: dict
) -> MatchResult:
    """Evaluate one patient against one trial's parsed rules."""
    result = MatchResult(
        patient_id         = patient_row["patient_id"],
        trial_id           = trial_row["trial_id"],
        nct_id             = trial_row["nct_id"],
        trial_title        = trial_row["title"],
        primary_indication = trial_row["primary_indication"],
        phase              = trial_row["phase"],
    )

    # Inclusion criteria
    for criterion in rules.get("inclusion_criteria", []):
        cr = evaluate_criterion(criterion, patient_data, patient_row)
        if cr.passed:
            result.matched_criteria.append(cr)
        else:
            result.disqualifiers.append(cr)

    # Exclusion criteria — passing an exclusion = disqualified
    for criterion in rules.get("exclusion_criteria", []):
        cr = evaluate_criterion(criterion, patient_data, patient_row)
        if cr.passed:
            cr.reason = f"[EXCLUSION MET] {cr.reason}"
            result.disqualifiers.append(cr)

    return result


def results_to_df(results: list[MatchResult]) -> pd.DataFrame:
    """Convert MatchResult list to DataFrame for DuckDB insertion."""
    rows = []
    for r in results:
        rows.append({
            "match_id":                 r.patient_id + "_" + r.trial_id,
            "patient_id":               r.patient_id,
            "trial_id":                 r.trial_id,
            "nct_id":                   r.nct_id,
            "trial_title":              r.trial_title,
            "primary_indication":       r.primary_indication,
            "phase":                    r.phase,
            "match_score":              r.match_score,
            "matched_criteria_count":   len(r.matched_criteria),
            "total_inclusion_criteria": r.total_inclusion_criteria,
            "disqualifier_count":       len(r.disqualifiers),
            "matched_criteria_json":    json.dumps([
                {"id": c.criterion_id, "reason": c.reason}
                for c in r.matched_criteria
            ]),
            "disqualifiers_json":       json.dumps([
                {"id": c.criterion_id, "reason": c.reason}
                for c in r.disqualifiers
            ]),
            "is_fully_eligible":        r.is_fully_eligible,
            "evaluated_at":             r.evaluated_at,
        })
    return pd.DataFrame(rows)


def run_matching(db_path: str = None, limit_patients: int = None):
    """
    Full matching run: parse all trial criteria, evaluate all patients,
    write results to gold.engine_output in DuckDB.
    """
    db_path = db_path or str(DB_PATH)
    con = duckdb.connect(db_path)

    print("\n🔬 Starting eligibility matching run\n")

    # Load trials
    trials = con.execute(
        "SELECT * FROM main_silver.dim_trials WHERE is_recruiting = true"
    ).df()
    print(f"  Trials to match: {len(trials)}")

    # Load patients
    query = "SELECT * FROM main_silver.dim_patients"
    if limit_patients:
        query += f" LIMIT {int(limit_patients)}"
    patients = con.execute(query).df()
    print(f"  Patients to evaluate: {len(patients)}")
    print()

    all_results = []

    for _, trial in trials.iterrows():
        print(f"  📋 {trial['nct_id']} — {trial['title'][:60]}...")

        # Parse criteria via Claude API
        try:
            rules = parse_criteria(trial["criteria_text"], trial_id=trial["nct_id"])
        except Exception as e:
            print(f"     ⚠️  Parse failed: {e}")
            continue

        # Evaluate each patient
        matched_count = 0
        for _, patient in patients.iterrows():
            patient_data = load_patient_clinical_data(con, patient["patient_id"])
            result = evaluate_patient_for_trial(patient, trial, rules, patient_data)
            all_results.append(result)
            if result.is_fully_eligible:
                matched_count += 1

        print(f"     → {matched_count}/{len(patients)} fully eligible "
              f"({matched_count/len(patients)*100:.1f}%)\n")

    # Write to DuckDB gold layer
    if all_results:
        results_df = results_to_df(all_results)
        con.execute("CREATE SCHEMA IF NOT EXISTS gold")
        con.execute("""
            CREATE OR REPLACE TABLE gold.engine_output AS
            SELECT * FROM results_df
        """)
        total_eligible = results_df["is_fully_eligible"].sum()
        print(f"✅ Matching complete.")
        print(f"   {len(all_results):,} patient×trial pairs evaluated")
        print(f"   {total_eligible:,} fully eligible matches written to gold.engine_output\n")
    else:
        print("⚠️  No results to write.")

    con.close()
    return all_results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None,
                        help="Limit patients for testing (e.g. --limit 50)")
    args = parser.parse_args()
    run_matching(limit_patients=args.limit)