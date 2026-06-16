"""
tests/test_evaluators.py
-------------------------
Unit tests for individual criterion evaluators.
"""

import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from eligibility.evaluators.lab_evaluator import evaluate_lab
from eligibility.evaluators.biomarker_evaluator import evaluate_biomarker
from eligibility.evaluators.medication_evaluator import evaluate_medication


# ── Lab evaluator ─────────────────────────────────────────────────────────────

class TestLabEvaluator:

    LABS = {
        "platelet_count": {"value": 180.0, "normal_high": 400.0, "normal_low": 150.0},
        "creatinine":     {"value": 0.9,   "normal_high": 1.2,   "normal_low": 0.6},
        "alt":            {"value": 120.0, "normal_high": 56.0,  "normal_low": 7.0},
    }

    def test_gte_passes(self):
        c = {"criterion_id": "IC_001", "field": "platelet_count",
             "operator": "gte", "value": 100, "uln_multiplier": None}
        r = evaluate_lab(c, self.LABS)
        assert r.passed is True

    def test_gte_fails(self):
        c = {"criterion_id": "IC_001", "field": "platelet_count",
             "operator": "gte", "value": 200, "uln_multiplier": None}
        r = evaluate_lab(c, self.LABS)
        assert r.passed is False

    def test_uln_passes(self):
        # creatinine 0.9 <= 1.5 * 1.2 (ULN) = 1.8 → passes
        c = {"criterion_id": "IC_002", "field": "creatinine",
             "operator": "lte", "value": None, "uln_multiplier": 1.5}
        r = evaluate_lab(c, self.LABS)
        assert r.passed is True

    def test_uln_fails(self):
        # alt 120 <= 2.5 * 56 = 140 → passes — change ULN to 1.0x to fail
        c = {"criterion_id": "IC_003", "field": "alt",
             "operator": "lte", "value": None, "uln_multiplier": 1.0}
        r = evaluate_lab(c, self.LABS)
        assert r.passed is False  # 120 > 1.0 * 56 = 56

    def test_missing_lab_fails(self):
        c = {"criterion_id": "IC_004", "field": "egfr",
             "operator": "gte", "value": 45, "uln_multiplier": None}
        r = evaluate_lab(c, self.LABS)
        assert r.passed is False
        assert "not found" in r.reason

    def test_actual_value_returned(self):
        c = {"criterion_id": "IC_001", "field": "platelet_count",
             "operator": "gte", "value": 100, "uln_multiplier": None}
        r = evaluate_lab(c, self.LABS)
        assert r.actual_value == 180.0


# ── Biomarker evaluator ───────────────────────────────────────────────────────

class TestBiomarkerEvaluator:

    BIOMARKERS = {
        "her2_status":       "positive",
        "egfr_mutation":     "exon19del",
        "pdl1_expression":   "high",
        "msi_status":        "msi-h",
        "kras_mutation":     "wildtype",
    }

    def test_eq_passes(self):
        c = {"criterion_id": "IC_001", "field": "her2_status",
             "operator": "eq", "value": "positive"}
        assert evaluate_biomarker(c, self.BIOMARKERS).passed is True

    def test_eq_fails(self):
        c = {"criterion_id": "IC_001", "field": "her2_status",
             "operator": "eq", "value": "negative"}
        assert evaluate_biomarker(c, self.BIOMARKERS).passed is False

    def test_in_passes(self):
        c = {"criterion_id": "IC_002", "field": "egfr_mutation",
             "operator": "in", "value": ["exon19del", "l858r"]}
        assert evaluate_biomarker(c, self.BIOMARKERS).passed is True

    def test_not_in_passes(self):
        c = {"criterion_id": "EC_001", "field": "kras_mutation",
             "operator": "not_in", "value": ["G12D", "G12V"]}
        assert evaluate_biomarker(c, self.BIOMARKERS).passed is True

    def test_not_in_fails(self):
        c = {"criterion_id": "EC_001", "field": "egfr_mutation",
             "operator": "not_in", "value": ["exon19del", "l858r"]}
        assert evaluate_biomarker(c, self.BIOMARKERS).passed is False

    def test_missing_biomarker_fails(self):
        c = {"criterion_id": "IC_003", "field": "alk_rearrangement",
             "operator": "eq", "value": "positive"}
        r = evaluate_biomarker(c, self.BIOMARKERS)
        assert r.passed is False


# ── Medication evaluator ──────────────────────────────────────────────────────

class TestMedicationEvaluator:

    MEDS = [
        {"drug_name": "doxorubicin", "drug_class": "anthracycline",
         "line_of_therapy": 1, "start_date": "2021-01-01", "end_date": "2021-06-01"},
        {"drug_name": "carboplatin", "drug_class": "platinum_compound",
         "line_of_therapy": 2, "start_date": "2022-01-01", "end_date": "2022-06-01"},
    ]

    def test_never_administered_fails_when_drug_present(self):
        c = {"criterion_id": "EC_001", "type": "medication_history",
             "operator": "never_administered", "value": "anthracycline"}
        r = evaluate_medication(c, self.MEDS)
        assert r.passed is False  # patient HAS prior anthracycline

    def test_never_administered_passes_when_drug_absent(self):
        c = {"criterion_id": "EC_002", "type": "medication_history",
             "operator": "never_administered", "value": "checkpoint_inhibitor"}
        r = evaluate_medication(c, self.MEDS)
        assert r.passed is True  # patient has NOT had checkpoint inhibitor

    def test_required_passes_when_drug_present(self):
        c = {"criterion_id": "IC_001", "type": "medication_history",
             "operator": "required", "value": "platinum_compound"}
        r = evaluate_medication(c, self.MEDS)
        assert r.passed is True

    def test_required_fails_when_drug_absent(self):
        c = {"criterion_id": "IC_001", "type": "medication_history",
             "operator": "required", "value": "egfr_inhibitor"}
        r = evaluate_medication(c, self.MEDS)
        assert r.passed is False

    def test_specific_drug_name_check(self):
        c = {"criterion_id": "EC_003", "type": "medication_history",
             "field": "drug_name", "operator": "neq", "value": "osimertinib"}
        r = evaluate_medication(c, self.MEDS)
        assert r.passed is True  # osimertinib not in history