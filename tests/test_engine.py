"""
tests/test_engine.py
---------------------
Unit tests for the eligibility matching engine logic.
No DuckDB or API calls — tests pure evaluation logic.
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from eligibility.models import MatchResult, CriterionResult
from eligibility.engine import evaluate_criterion, evaluate_patient_for_trial, _compare_numeric


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def patient_row():
    return pd.Series({
        "patient_id":        "pt-001",
        "ecog_status":       1,
        "age_at_diagnosis":  58,
        "primary_cancer":    "Lung",
        "stage_at_dx":       "IV",
        "is_metastatic":     True,
        "gender":            "M",
    })


@pytest.fixture
def patient_data():
    return {
        "labs": {
            "platelet_count": {"value": 180.0, "normal_high": 400.0, "normal_low": 150.0},
            "hemoglobin":     {"value": 12.5,  "normal_high": 17.5,  "normal_low": 11.5},
            "creatinine":     {"value": 0.9,   "normal_high": 1.2,   "normal_low": 0.6},
            "alt":            {"value": 35.0,  "normal_high": 56.0,  "normal_low": 7.0},
        },
        "biomarkers": {
            "pdl1_expression":        "high",
            "egfr_mutation":          "wildtype",
            "alk_rearrangement":      "negative",
            "her2_status":            "negative",
        },
        "medications": [
            {"drug_name": "carboplatin", "drug_class": "platinum_compound",
             "line_of_therapy": 1, "start_date": "2022-01-01", "end_date": "2022-06-01",
             "discontinuation_reason": "completed", "is_prior_anthracycline": False,
             "is_prior_immunotherapy": False, "is_prior_egfr_inhibitor": False,
             "is_prior_cdk46_inhibitor": False, "is_prior_osimertinib": False,
             "is_prior_trastuzumab": False},
        ]
    }


@pytest.fixture
def trial_row():
    return pd.Series({
        "trial_id":           "trial-001",
        "nct_id":             "NCT04000001",
        "title":              "Phase III NSCLC Trial",
        "primary_indication": "Non-Small Cell Lung Cancer",
        "phase":              "Phase III",
    })


# ── _compare_numeric ──────────────────────────────────────────────────────────

class TestCompareNumeric:
    def test_lte_passes(self):  assert _compare_numeric(1, "lte", 2) is True
    def test_lte_fails(self):   assert _compare_numeric(3, "lte", 2) is False
    def test_gte_passes(self):  assert _compare_numeric(5, "gte", 3) is True
    def test_eq_passes(self):   assert _compare_numeric(2, "eq",  2) is True
    def test_gt_passes(self):   assert _compare_numeric(3, "gt",  2) is True
    def test_unknown_op(self):  assert _compare_numeric(1, "xyz", 2) is False


# ── ECOG evaluation ───────────────────────────────────────────────────────────

class TestEcogEvaluation:

    def test_ecog_passes_when_within_limit(self, patient_row, patient_data):
        criterion = {"criterion_id": "IC_001", "type": "ecog",
                     "field": "ecog_status", "operator": "lte", "value": 2}
        result = evaluate_criterion(criterion, patient_data, patient_row)
        assert result.passed is True

    def test_ecog_fails_when_above_limit(self, patient_data):
        patient_row_ecog3 = pd.Series({"patient_id": "pt-x", "ecog_status": 3,
                                       "age_at_diagnosis": 50})
        criterion = {"criterion_id": "IC_001", "type": "ecog",
                     "field": "ecog_status", "operator": "lte", "value": 1}
        result = evaluate_criterion(criterion, patient_data, patient_row_ecog3)
        assert result.passed is False

    def test_ecog_result_has_actual_value(self, patient_row, patient_data):
        criterion = {"criterion_id": "IC_001", "type": "ecog",
                     "field": "ecog_status", "operator": "lte", "value": 2}
        result = evaluate_criterion(criterion, patient_data, patient_row)
        assert result.actual_value == 1


# ── Lab evaluation ────────────────────────────────────────────────────────────

class TestLabEvaluation:

    def test_lab_passes_absolute_threshold(self, patient_row, patient_data):
        criterion = {"criterion_id": "IC_002", "type": "lab",
                     "field": "platelet_count", "operator": "gte",
                     "value": 100, "uln_multiplier": None}
        result = evaluate_criterion(criterion, patient_data, patient_row)
        assert result.passed is True  # 180 >= 100

    def test_lab_fails_absolute_threshold(self, patient_row, patient_data):
        criterion = {"criterion_id": "IC_002", "type": "lab",
                     "field": "platelet_count", "operator": "gte",
                     "value": 200, "uln_multiplier": None}
        result = evaluate_criterion(criterion, patient_data, patient_row)
        assert result.passed is False  # 180 < 200

    def test_lab_uln_based_threshold_passes(self, patient_row, patient_data):
        # creatinine 0.9, normal_high 1.2 → 1.5x ULN = 1.8 → 0.9 <= 1.8 ✓
        criterion = {"criterion_id": "IC_003", "type": "lab",
                     "field": "creatinine", "operator": "lte",
                     "value": None, "uln_multiplier": 1.5}
        result = evaluate_criterion(criterion, patient_data, patient_row)
        assert result.passed is True

    def test_missing_lab_returns_failed(self, patient_row, patient_data):
        criterion = {"criterion_id": "IC_004", "type": "lab",
                     "field": "egfr", "operator": "gte",
                     "value": 60, "uln_multiplier": None}
        result = evaluate_criterion(criterion, patient_data, patient_row)
        assert result.passed is False
        assert "not found" in result.reason


# ── Biomarker evaluation ──────────────────────────────────────────────────────

class TestBiomarkerEvaluation:

    def test_biomarker_eq_passes(self, patient_row, patient_data):
        criterion = {"criterion_id": "IC_005", "type": "biomarker",
                     "field": "pdl1_expression", "operator": "eq", "value": "high"}
        result = evaluate_criterion(criterion, patient_data, patient_row)
        assert result.passed is True

    def test_biomarker_eq_fails(self, patient_row, patient_data):
        criterion = {"criterion_id": "IC_006", "type": "biomarker",
                     "field": "her2_status", "operator": "eq", "value": "positive"}
        result = evaluate_criterion(criterion, patient_data, patient_row)
        assert result.passed is False

    def test_biomarker_not_in_exclusion(self, patient_row, patient_data):
        # Patient has wildtype EGFR → passes "not in [exon19del, L858R]"
        criterion = {"criterion_id": "EC_001", "type": "biomarker",
                     "field": "egfr_mutation", "operator": "not_in",
                     "value": ["exon19del", "l858r"]}
        result = evaluate_criterion(criterion, patient_data, patient_row)
        assert result.passed is True


# ── Full patient×trial evaluation ─────────────────────────────────────────────

class TestFullEvaluation:

    def test_match_score_between_0_and_1(self, patient_row, trial_row, patient_data):
        rules = {
            "inclusion_criteria": [
                {"criterion_id": "IC_001", "type": "ecog",
                 "field": "ecog_status", "operator": "lte", "value": 2},
                {"criterion_id": "IC_002", "type": "lab",
                 "field": "platelet_count", "operator": "gte",
                 "value": 100, "uln_multiplier": None},
            ],
            "exclusion_criteria": []
        }
        result = evaluate_patient_for_trial(patient_row, trial_row, rules, patient_data)
        assert 0.0 <= result.match_score <= 1.0

    def test_fully_eligible_when_all_inclusion_met_no_exclusions(
            self, patient_row, trial_row, patient_data):
        rules = {
            "inclusion_criteria": [
                {"criterion_id": "IC_001", "type": "ecog",
                 "field": "ecog_status", "operator": "lte", "value": 2},
            ],
            "exclusion_criteria": []
        }
        result = evaluate_patient_for_trial(patient_row, trial_row, rules, patient_data)
        assert result.is_fully_eligible is True

    def test_not_eligible_when_exclusion_met(self, patient_row, trial_row, patient_data):
        # Patient has wildtype EGFR — if trial EXCLUDES wildtype, patient is disqualified
        rules = {
            "inclusion_criteria": [
                {"criterion_id": "IC_001", "type": "ecog",
                 "field": "ecog_status", "operator": "lte", "value": 2},
            ],
            "exclusion_criteria": [
                {"criterion_id": "EC_001", "type": "biomarker",
                 "field": "egfr_mutation", "operator": "eq", "value": "wildtype"},
            ]
        }
        result = evaluate_patient_for_trial(patient_row, trial_row, rules, patient_data)
        assert result.is_fully_eligible is False

    def test_match_result_has_correct_ids(self, patient_row, trial_row, patient_data):
        rules = {"inclusion_criteria": [], "exclusion_criteria": []}
        result = evaluate_patient_for_trial(patient_row, trial_row, rules, patient_data)
        assert result.patient_id == "pt-001"
        assert result.trial_id   == "trial-001"
        assert result.nct_id     == "NCT04000001"


# ── MatchResult model ─────────────────────────────────────────────────────────

class TestMatchResultModel:

    def test_match_score_zero_with_no_criteria(self):
        r = MatchResult("p1", "t1", "NCT001", "Trial", "Lung", "Phase II")
        assert r.match_score == 0.0

    def test_match_score_1_when_all_pass(self):
        r = MatchResult("p1", "t1", "NCT001", "Trial", "Lung", "Phase II")
        r.matched_criteria = [CriterionResult("IC_001", True, "passes")]
        assert r.match_score == 1.0

    def test_match_score_half(self):
        r = MatchResult("p1", "t1", "NCT001", "Trial", "Lung", "Phase II")
        r.matched_criteria = [CriterionResult("IC_001", True, "passes")]
        r.disqualifiers    = [CriterionResult("IC_002", False, "fails")]
        assert r.match_score == 0.5

    def test_is_fully_eligible_requires_no_disqualifiers(self):
        r = MatchResult("p1", "t1", "NCT001", "Trial", "Lung", "Phase II")
        r.matched_criteria = [CriterionResult("IC_001", True, "passes")]
        r.disqualifiers    = []
        assert r.is_fully_eligible is True

    def test_is_not_eligible_with_disqualifier(self):
        r = MatchResult("p1", "t1", "NCT001", "Trial", "Lung", "Phase II")
        r.matched_criteria = [CriterionResult("IC_001", True, "passes")]
        r.disqualifiers    = [CriterionResult("EC_001", True, "exclusion met")]
        assert r.is_fully_eligible is False