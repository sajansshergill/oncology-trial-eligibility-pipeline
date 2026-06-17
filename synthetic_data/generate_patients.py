"""
generate_patients.py
Generates synthetic oncology patient records modeled after OMOP CDM.
Usage: python synthetic_data/generate_patients.py --n 1000
"""
import argparse, random, uuid
from datetime import date, timedelta
from pathlib import Path
import pandas as pd
import numpy as np
from faker import Faker
try:
    from synthetic_data.oncology_codes import (
        ICD10_ONCOLOGY,
        LOINC_LABS,
        RXNORM_MEDICATIONS,
        BIOMARKER_PROFILES,
    )
except ModuleNotFoundError:
    from oncology_codes import (
        ICD10_ONCOLOGY,
        LOINC_LABS,
        RXNORM_MEDICATIONS,
        BIOMARKER_PROFILES,
    )

fake = Faker()
Faker.seed(42); random.seed(42); np.random.seed(42)

OUTPUT_DIR = Path(__file__).parent.parent / "data" / "raw"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def random_date(start, end):
    return start + timedelta(days=random.randint(0, (end - start).days))

def weighted_choice(options, weight_key="weight"):
    return random.choices(options, weights=[o[weight_key] for o in options], k=1)[0]

def skewed_lab_value(lab, abnormal_prob=0.25):
    if random.random() < abnormal_prob:
        val = random.uniform(lab["low"], lab["normal_low"]) if random.random() < 0.5 \
              else random.uniform(lab["normal_high"], lab["high"])
    else:
        val = random.uniform(lab["normal_low"], lab["normal_high"])
    return round(val, 2)

def generate_patients(n):
    print(f"  Generating {n} patients...")
    records = []
    for _ in range(n):
        dob = fake.date_of_birth(minimum_age=18, maximum_age=85)
        dx  = random.choice(ICD10_ONCOLOGY)
        gender = random.choices(["M","F"], weights=[0.48,0.52] if dx["category"]!="Prostate" else [1.0,0.0])[0]
        records.append({
            "patient_id":     str(uuid.uuid4()),
            "birth_date":     dob.isoformat(),
            "gender":         gender,
            "race":           random.choice(["White","Black or African American","Asian","Hispanic or Latino","Other"]),
            "ethnicity":      random.choice(["Not Hispanic or Latino","Hispanic or Latino"]),
            "state":          fake.state_abbr(),
            "zip_code":       fake.zipcode(),
            "ecog_status":    random.choices([0,1,2,3], weights=[0.30,0.40,0.20,0.10])[0],
            "smoking_status": random.choice(["never","former","current"]),
            "primary_cancer": dx["category"],
            "index_icd10":    dx["code"],
            "stage_at_dx":    random.choices(["I","II","III","IV"], weights=[0.15,0.20,0.25,0.40])[0],
            "diagnosis_date": random_date(date(2015,1,1), date(2024,6,1)).isoformat(),
            "is_metastatic":  random.choices([True,False], weights=[0.45,0.55])[0],
            "source_file":    "patients.parquet",
        })
    return pd.DataFrame(records)

def generate_diagnoses(patients):
    print("  Generating diagnoses...")
    records = []
    comorbid = [("E11.9","T2DM"),("I10","HTN"),("J44.1","COPD"),("N18.3","CKD3"),("F32.9","MDD"),("E78.5","HLD")]
    for _, pt in patients.iterrows():
        records.append({"diagnosis_id": str(uuid.uuid4()), "patient_id": pt["patient_id"],
                        "icd10_code": pt["index_icd10"], "diagnosis_date": pt["diagnosis_date"],
                        "diagnosis_type": "primary", "source_file": "diagnoses.parquet"})
        for code, _ in random.sample(comorbid, random.choices([0,1,2,3], weights=[0.30,0.35,0.25,0.10])[0]):
            dx_date = random_date(date.fromisoformat(pt["diagnosis_date"]) - timedelta(days=365*5),
                                  date.fromisoformat(pt["diagnosis_date"]))
            records.append({"diagnosis_id": str(uuid.uuid4()), "patient_id": pt["patient_id"],
                            "icd10_code": code, "diagnosis_date": dx_date.isoformat(),
                            "diagnosis_type": "comorbidity", "source_file": "diagnoses.parquet"})
    return pd.DataFrame(records)

def generate_labs(patients):
    print("  Generating lab results...")
    records = []
    for _, pt in patients.iterrows():
        dx_date = date.fromisoformat(pt["diagnosis_date"])
        for i in range(random.randint(3, 8)):
            panel_date = dx_date + timedelta(days=i * random.randint(14, 60))
            if panel_date > date.today(): break
            for lab in random.sample(LOINC_LABS, k=random.randint(4, len(LOINC_LABS))):
                records.append({"lab_id": str(uuid.uuid4()), "patient_id": pt["patient_id"],
                                "loinc_code": lab["code"], "lab_name": lab["name"],
                                "value": skewed_lab_value(lab), "unit": lab["unit"],
                                "lab_date": panel_date.isoformat(), "normal_low": lab["normal_low"],
                                "normal_high": lab["normal_high"], "is_abnormal": None,
                                "source_file": "labs.parquet"})
    return pd.DataFrame(records)

def generate_medications(patients):
    print("  Generating medication history...")
    cancer_to_classes = {
        "Breast":     ["taxane","anthracycline","monoclonal_antibody","cdk4_6_inhibitor","aromatase_inhibitor"],
        "Lung":       ["platinum_compound","taxane","egfr_inhibitor","checkpoint_inhibitor"],
        "Colorectal": ["platinum_compound","monoclonal_antibody","checkpoint_inhibitor"],
        "Prostate":   ["aromatase_inhibitor","taxane"],
        "Leukemia":   ["tyrosine_kinase_inhibitor","alkylating_agent"],
        "Lymphoma":   ["monoclonal_antibody","alkylating_agent"],
        "default":    ["platinum_compound","taxane","alkylating_agent"],
    }
    records = []
    for _, pt in patients.iterrows():
        dx_date = date.fromisoformat(pt["diagnosis_date"])
        classes = cancer_to_classes.get(pt["primary_cancer"], cancer_to_classes["default"])
        meds    = [m for m in RXNORM_MEDICATIONS if m["class"] in classes] or RXNORM_MEDICATIONS[:5]
        line_start = dx_date + timedelta(days=random.randint(14, 45))
        for line in range(1, random.randint(1, 4) + 1):
            line_end = line_start + timedelta(days=random.randint(60, 365))
            for med in random.sample(meds, k=min(random.randint(1, 3), len(meds))):
                records.append({"medication_id": str(uuid.uuid4()), "patient_id": pt["patient_id"],
                                "rxnorm_code": med["code"], "drug_name": med["name"],
                                "drug_class": med["class"], "route": med["route"],
                                "line_of_therapy": line, "start_date": line_start.isoformat(),
                                "end_date": line_end.isoformat(),
                                "discontinuation_reason": random.choice(["completed","progression","toxicity","patient_preference","completed"]),
                                "source_file": "medications.parquet"})
            line_start = line_end + timedelta(days=random.randint(7, 30))
            if line_start > date.today(): break
    return pd.DataFrame(records)

def generate_biomarkers(patients):
    print("  Generating biomarker profiles...")
    records = []
    for _, pt in patients.iterrows():
        cancer   = pt["primary_cancer"]
        profiles = BIOMARKER_PROFILES.get(cancer, BIOMARKER_PROFILES["default"])
        profile  = weighted_choice(profiles)
        records.append({"biomarker_id": str(uuid.uuid4()), "patient_id": pt["patient_id"],
                        "cancer_type": cancer, "test_date": pt["diagnosis_date"],
                        "source_file": "biomarkers.parquet",
                        **{k: v for k, v in profile.items() if k != "weight"}})
    return pd.DataFrame(records)

def main(n):
    print(f"\n🧬 Generating synthetic oncology dataset — {n} patients\n")
    patients    = generate_patients(n)
    diagnoses   = generate_diagnoses(patients)
    labs        = generate_labs(patients)
    medications = generate_medications(patients)
    biomarkers  = generate_biomarkers(patients)
    datasets    = {"patients": patients, "diagnoses": diagnoses, "labs": labs,
                   "medications": medications, "biomarkers": biomarkers}
    print("\n  Writing Parquet files to data/raw/...")
    for name, df in datasets.items():
        path = OUTPUT_DIR / f"{name}.parquet"
        df.to_parquet(path, index=False)
        print(f"  ✓ {name}.parquet — {len(df):,} rows")
    print(f"\n✅ Done. Files written to {OUTPUT_DIR}\n")
    return datasets

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=1000)
    args = parser.parse_args()
    main(args.n)