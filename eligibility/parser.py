"""
eligibility/parser.py
---------------------
Sends free-text eligibility criteria to the Claude API and returns
a structured JSON rule set for the matching engine to evaluate.
"""

import json
import os
import anthropic

_client = None

def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    return _client


SYSTEM_PROMPT = """You are a clinical data parser specializing in oncology clinical trial eligibility criteria.

Your task: convert free-text eligibility criteria into a structured JSON object.

Return ONLY valid JSON with this exact schema — no markdown, no explanation:

{
  "inclusion_criteria": [
    {
      "criterion_id": "IC_001",
      "type": "ecog | lab | biomarker | medication_history | diagnosis | age | other",
      "field": "exact field name from patient data",
      "operator": "eq | neq | lte | gte | lt | gt | in | not_in | never_administered | required | positive | negative",
      "value": <number, string, or list>,
      "unit": "<unit string or null>",
      "uln_multiplier": <number or null>,
      "notes": "<optional clarification>"
    }
  ],
  "exclusion_criteria": [
    {
      "criterion_id": "EC_001",
      "type": "ecog | lab | biomarker | medication_history | diagnosis | age | other",
      "field": "exact field name",
      "operator": "eq | neq | lte | gte | lt | gt | in | not_in | never_administered | required | positive | negative",
      "value": <number, string, or list>,
      "unit": "<unit string or null>",
      "uln_multiplier": <number or null>,
      "notes": "<optional clarification>"
    }
  ]
}

Field name conventions to use:
- ecog_status (integer 0-4)
- platelet_count (10^9/L)
- hemoglobin (g/dL)
- creatinine (mg/dL)
- alt (U/L)
- total_bilirubin (mg/dL)
- egfr (mL/min)
- her2_status (positive/negative)
- er_status (positive/negative)
- pr_status (positive/negative)
- egfr_mutation (exon19del/L858R/wildtype)
- alk_rearrangement (positive/negative)
- pdl1_expression (high/medium/low)
- kras_mutation (wildtype/G12D/G12V/other)
- msi_status (MSI-H/MSS)
- drug_class (anthracycline/taxane/checkpoint_inhibitor/egfr_inhibitor/cdk4_6_inhibitor etc.)
- drug_name (specific drug name)
- primary_cancer (Lung/Breast/Colorectal/etc.)
- stage_at_dx (I/II/III/IV)
- is_metastatic (true/false)
- age_at_diagnosis (years)

For ULN-based lab criteria like "creatinine <= 1.5x ULN", set uln_multiplier to 1.5 and value to null."""


def parse_criteria(criteria_text: str, trial_id: str = "") -> dict:
    """
    Parse free-text eligibility criteria into structured JSON rules.

    Args:
        criteria_text: Raw eligibility criteria from trial registry
        trial_id: Optional trial ID for logging

    Returns:
        dict with 'inclusion_criteria' and 'exclusion_criteria' lists
    """
    client = _get_client()

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"Parse these eligibility criteria:\n\n{criteria_text}"
            }
        ]
    )

    raw = message.content[0].text.strip()

    # Strip any accidental markdown fences
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    parsed = json.loads(raw)

    # Validate structure
    if "inclusion_criteria" not in parsed:
        parsed["inclusion_criteria"] = []
    if "exclusion_criteria" not in parsed:
        parsed["exclusion_criteria"] = []

    print(f"  ✓ Parsed {len(parsed['inclusion_criteria'])} inclusion + "
          f"{len(parsed['exclusion_criteria'])} exclusion criteria"
          + (f" for {trial_id}" if trial_id else ""))

    return parsed


if __name__ == "__main__":
    # Quick smoke test
    sample = (
        "ECOG performance status 0 or 1. PD-L1 expression >= 50%. "
        "Platelet count >= 100 x 10^9/L. Creatinine <= 1.5x ULN. "
        "No prior anti-PD-1 therapy. No EGFR sensitizing mutation."
    )
    result = parse_criteria(sample, trial_id="TEST")
    print(json.dumps(result, indent=2))