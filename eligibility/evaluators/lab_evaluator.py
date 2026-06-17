"""
eligibility/evaluators/lab_evaluator.py
----------------------------------------
Evaluates lab-based eligibility criteria against patient's most recent lab values.
"""

from eligibility.models import CriterionResult


def evaluate_lab(criterion: dict, patient_labs: dict) -> CriterionResult:
    """
    Evaluate a single lab criterion against the patient's most recent lab values.

    patient_labs: dict of {lab_name: {"value": float, "normal_high": float, "normal_low": float}}
    """
    cid      = criterion["criterion_id"]
    field    = criterion["field"]
    operator = criterion["operator"]
    value    = criterion.get("value")
    uln_mult = criterion.get("uln_multiplier")

    if field not in patient_labs:
        return CriterionResult(
            criterion_id=cid, passed=False,
            reason=f"Lab '{field}' not found in patient record",
            actual_value=None
        )

    lab_rec     = patient_labs[field]
    actual      = lab_rec["value"]
    normal_high = lab_rec.get("normal_high")
    normal_low  = lab_rec.get("normal_low")

    # ULN-based threshold (e.g. "creatinine <= 1.5x ULN")
    if uln_mult is not None and normal_high is not None:
        threshold = uln_mult * normal_high
        passed = _compare(actual, operator, threshold)
        reason = (f"{field} {actual} {'passes' if passed else 'fails'} "
                  f"{operator} {uln_mult}x ULN ({threshold:.2f})")
        return CriterionResult(criterion_id=cid, passed=passed,
                               reason=reason, actual_value=actual)

    # Absolute threshold
    if value is not None:
        passed = _compare(actual, operator, float(value))
        reason = (f"{field} {actual} {'passes' if passed else 'fails'} "
                  f"{operator} {value}")
        return CriterionResult(criterion_id=cid, passed=passed,
                               reason=reason, actual_value=actual)

    return CriterionResult(criterion_id=cid, passed=False,
                           reason=f"No threshold defined for {field}",
                           actual_value=actual)


def _compare(actual: float, operator: str, threshold: float) -> bool:
    ops = {
        "lte": actual <= threshold,
        "gte": actual >= threshold,
        "lt":  actual <  threshold,
        "gt":  actual >  threshold,
        "eq":  actual == threshold,
        "neq": actual != threshold,
    }
    return ops.get(operator, False)