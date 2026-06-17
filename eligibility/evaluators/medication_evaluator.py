"""
eligibility/evaluators/medication_evaluator.py
-----------------------------------------------
Evaluates medication history criteria (prior therapy flags).
"""

from eligibility.models import CriterionResult


def evaluate_medication(criterion: dict, patient_medications: list[dict]) -> CriterionResult:
    """
    Evaluate a medication history criterion.

    patient_medications: list of dicts with keys:
        drug_name, drug_class, line_of_therapy, start_date, end_date,
        discontinuation_reason, is_prior_anthracycline, etc.
    """
    cid      = criterion["criterion_id"]
    operator = criterion["operator"]
    field    = criterion.get("field", "")
    value    = criterion.get("value")

    # --- never_administered (patient must NOT have had this) ---
    if operator == "never_administered":
        drug_class = criterion.get("value") or criterion.get("drug_class", "")
        drug_name  = criterion.get("drug_name", "")

        has_prior = any(
            (drug_class and m.get("drug_class", "").lower() == drug_class.lower())
            or (drug_name and m.get("drug_name", "").lower() == drug_name.lower())
            for m in patient_medications
        )
        passed = not has_prior
        reason = (
            f"No prior {drug_class or drug_name} found (passes)"
            if passed else
            f"Prior {drug_class or drug_name} therapy found (disqualifies)"
        )
        return CriterionResult(criterion_id=cid, passed=passed,
                               reason=reason, actual_value=has_prior)

    # --- required (must have received this therapy) ---
    if operator == "required":
        drug_class = criterion.get("value") or criterion.get("drug_class", "")
        has_it = any(
            m.get("drug_class", "").lower() == drug_class.lower()
            for m in patient_medications
        )
        passed = has_it
        reason = (
            f"Prior {drug_class} therapy confirmed (passes)"
            if passed else
            f"No prior {drug_class} therapy found (fails)"
        )
        return CriterionResult(criterion_id=cid, passed=passed,
                               reason=reason, actual_value=has_it)

    # --- specific drug name check ---
    if field == "drug_name" and value:
        has_drug = any(
            m.get("drug_name", "").lower() == str(value).lower()
            for m in patient_medications
        )
        if operator in ("eq", "required"):
            passed = has_drug
        elif operator in ("neq", "never_administered"):
            passed = not has_drug
        else:
            passed = not has_drug
        reason = f"Drug '{value}': {'found' if has_drug else 'not found'} in history"
        return CriterionResult(criterion_id=cid, passed=passed,
                               reason=reason, actual_value=has_drug)

    return CriterionResult(criterion_id=cid, passed=True,
                           reason=f"Medication criterion not evaluated (unknown pattern)",
                           actual_value=None)