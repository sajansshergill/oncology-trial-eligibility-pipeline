"""
generate_trials.py
------------------
Generates synthetic clinical trial registry records.
Outputs trials.json to data/raw/ for Bronze layer ingestion.

Usage:
  python synthetic_data/generate_trials.py
"""

import json
import uuid
from pathlib import Path
from datetime import date, timedelta
import random

from oncology_codes import SAMPLE_TRIAL_CRITERIA

OUTPUT_DIR = Path(__file__).parent.parent / "data" / "raw"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def generate_trials() -> list[dict]:
    print("  Generating clinical trial records...")
    trials = []
    for trial in SAMPLE_TRIAL_CRITERIA:
        start_date = date(2020, 1, 1) + timedelta(days=random.randint(0, 365 * 3))
        trials.append({
            "trial_id":            str(uuid.uuid4()),
            "nct_id":              trial["nct_id"],
            "title":               trial["title"],
            "phase":               trial["phase"],
            "primary_indication":  trial["indication"],
            "sponsor":             trial["sponsor"],
            "criteria_text":       trial["criteria_text"],
            "status":              random.choice(["Recruiting", "Recruiting", "Active, not recruiting"]),
            "start_date":          start_date.isoformat(),
            "estimated_end_date":  (start_date + timedelta(days=365 * random.randint(2, 5))).isoformat(),
            "target_enrollment":   random.choice([50, 100, 150, 200, 300, 500]),
            "source_file":         "trials.json",
        })
    return trials


def main():
    print("\n🔬 Generating clinical trial registry\n")
    trials = generate_trials()
    path = OUTPUT_DIR / "trials.json"
    with open(path, "w") as f:
        json.dump(trials, f, indent=2)
    print(f"  ✓ trials.json — {len(trials)} trials")
    print(f"\n✅ Done. Written to {path}\n")


if __name__ == "__main__":
    main()