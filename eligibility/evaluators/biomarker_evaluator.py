"""
eligibility/evaluators/biomarker_evaluator.py
----------------------------------------------
Evaluates biomarker/molecular criteria against patient's biomarker profile.
"""

from eligibility.models import CriterionResult


def evaluate_biomarker(criterion: dict, patient_biomarkers: dict) -> CriterionResult:
    """
    Evaluate a biomarker criterion.

    patient_biomarkers: dict of {field_name: value_string}
    e.g. {"her2_status": "positive", "egfr_mutation": "exon19del", ...}
    """
    cid      = criterion["criterion_id"]
    field    = criterion["field"]
    operator = criterion["operator"]
    value    = criterion.get("value")

    if field not in patient_biomarkers:
        return CriterionResult(
            criterion_id=cid, passed=False,
            reason=f"Biomarker '{field}' not found in patient record",
            actual_value=None
        )

    actual = str(patient_biomarkers[field]).lower()

    if operator == "eq" or operator == "positive":
        expected = str(value).lower() if value else "positive"
        passed   = actual == expected
        reason   = (f"{field} is '{actual}' — "
                    f"{'matches' if passed else 'does not match'} required '{expected}'")
        return CriterionResult(criterion_id=cid, passed=passed,
                               reason=reason, actual_value=actual)

    if operator == "neq" or operator == "negative":
        expected = str(value).lower() if value else "negative"
        passed   = actual != expected if operator == "neq" else actual == expected
        reason   = f"{field} is '{actual}'"
        return CriterionResult(criterion_id=cid, passed=passed,
                               reason=reason, actual_value=actual)

    if operator == "in":
        values = [str(v).lower() for v in (value if isinstance(value, list) else [value])]
        passed = actual in values
        reason = f"{field} '{actual}' {'in' if passed else 'not in'} {values}"
        return CriterionResult(criterion_id=cid, passed=passed,
                               reason=reason, actual_value=actual)

    if operator == "not_in":
        values = [str(v).lower() for v in (value if isinstance(value, list) else [value])]
        passed = actual not in values
        reason = (f"{field} '{actual}' "
                  f"{'not in (passes)' if passed else 'in excluded list (fails)'} {values}")
        return CriterionResult(criterion_id=cid, passed=passed,
                               reason=reason, actual_value=actual)

    return CriterionResult(criterion_id=cid, passed=False,
                           reason=f"Unknown operator '{operator}' for biomarker",
                           actual_value=actual)