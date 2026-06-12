# Oncology Clinical Trial Eligibility Screening Pipeline

> Automating patient-trial matching for oncology research using structured EHR data, dbt + DuckDB medallion architecture, and AI-assisted eligibility parsing via the Claude API.

---

## Overview

Clinical trial enrollment is one of the biggest bottlenecks in oncology drug development. Matching eligible patients to open trials is largely manual, error-prone, and slow — even at institutions with structured EHR data.

This pipeline ingests synthetic oncology patient records (modeled after OMOP CDM), applies a rules-based eligibility engine against open trial criteria, and delivers a ranked match dataset to a research-facing Streamlit dashboard. The eligibility criteria parser uses the Claude API to convert unstructured free-text trial criteria into structured, evaluable JSON rules.

**Target use case:** Life science partners and research oncologists who need to identify patient cohorts for clinical trials, FDA submission evidence packages, or peer-reviewed research — the exact customers Flatiron Health serves.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                      Data Sources                            │
│  Local CSV/Parquet (synthetic OMOP-adjacent):                │
│  patients, diagnoses, labs, medications, procedures          │
│  Trial registry JSONs: eligibility criteria free text        │
└───────────────────────┬──────────────────────────────────────┘
                        │  Prefect flow (Docker)
                        ▼
┌──────────────────────────────────────────────────────────────┐
│              DuckDB — Bronze Layer (raw.duckdb)              │
│  patients_raw, diagnoses_raw, labs_raw,                      │
│  medications_raw, trials_raw                                 │
└───────────────────────┬──────────────────────────────────────┘
                        │  dbt-duckdb models
                        ▼
┌──────────────────────────────────────────────────────────────┐
│              DuckDB — Silver Layer                           │
│  dim_patients, dim_diagnoses (ICD-10),                       │
│  dim_labs (LOINC), dim_medications (RxNorm), dim_trials      │
└───────────────────────┬──────────────────────────────────────┘
                        │  Python eligibility engine + Claude API
                        ▼
┌──────────────────────────────────────────────────────────────┐
│              DuckDB — Gold Layer                             │
│  fact_trial_matches:                                         │
│  patient_id | trial_id | match_score |                       │
│  matched_criteria | disqualifiers | evaluated_at             │
└───────────────────────┬──────────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────────────────┐
│              Streamlit Dashboard                             │
│  Filterable cohort explorer — queries DuckDB directly        │
└──────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Tool | Why |
|---|---|---|
| Orchestration | Prefect (Docker) | Lightweight, local-friendly; no Kubernetes needed |
| Storage & query | DuckDB | Columnar, zero-infra, reads Parquet/CSV natively |
| Transformation | dbt-duckdb | Medallion architecture + built-in test framework |
| Data quality | Great Expectations | Expectation suites between Silver and Gold |
| Eligibility parsing | Claude API | Free-text criteria → structured JSON rules |
| Matching engine | Python | Evaluates patient records against parsed rule sets |
| Dashboard | Streamlit | Direct DuckDB connection, zero backend needed |
| CI/CD | GitHub Actions | dbt compile + test on every PR |
| Containerization | Docker Compose | Reproducible local environment |

---

## Key Components

### 1. Data Ingestion (Prefect + DuckDB)

Prefect flows load CSV/Parquet files into DuckDB Bronze layer with full audit columns:

```python
# flows/ingest_patient_data.py
@flow(name="ingest-patient-data")
def ingest_patients(source_path: str = "data/raw/patients.parquet"):
    con = duckdb.connect("oncology.duckdb")
    con.execute(f"""
        CREATE OR REPLACE TABLE bronze.patients_raw AS
        SELECT
            *,
            current_timestamp AS ingested_at,
            '{source_path}'   AS source_file,
            gen_random_uuid() AS batch_id
        FROM read_parquet('{source_path}')
    """)
```

Separate flow handles trial registry ingestion, simulating a ClinicalTrials.gov feed.

### 2. Data Modeling (dbt-duckdb — Medallion Architecture)

```
models/
├── bronze/
│   ├── patients_raw.sql
│   ├── diagnoses_raw.sql
│   ├── labs_raw.sql
│   ├── medications_raw.sql
│   └── trials_raw.sql
├── silver/
│   ├── dim_patients.sql
│   ├── dim_diagnoses.sql       # ICD-10 normalization
│   ├── dim_labs.sql            # LOINC code mapping
│   ├── dim_medications.sql     # RxNorm normalization
│   └── dim_trials.sql          # Trial metadata + criteria text
└── gold/
    ├── fact_trial_matches.sql   # Core output: patient × trial scores
    └── mart_cohort_summary.sql  # Aggregate stats per trial
```

dbt tests applied at every layer:

```yaml
# silver/schema.yml
models:
  - name: dim_patients
    columns:
      - name: patient_id
        tests: [unique, not_null]
      - name: age_at_index
        tests:
          - dbt_utils.accepted_range:
              min_value: 0
              max_value: 120
  - name: dim_diagnoses
    columns:
      - name: icd10_code
        tests: [not_null, icd10_format]   # custom test
```

### 3. AI-Powered Eligibility Criteria Parser (Claude API)

Clinical trial eligibility criteria are authored in free text:

```
"ECOG performance status ≤ 2, HER2+ confirmed by IHC or FISH,
no prior anthracycline therapy, platelet count ≥ 100 × 10⁹/L"
```

The parser sends this to the Claude API and returns a structured rule set:

```json
{
  "inclusion_criteria": [
    {
      "criterion_id": "IC_001",
      "type": "lab_or_biomarker",
      "field": "ecog_performance_status",
      "operator": "lte",
      "value": 2
    },
    {
      "criterion_id": "IC_002",
      "type": "biomarker",
      "field": "her2_status",
      "operator": "eq",
      "value": "positive",
      "confirmation_methods": ["IHC", "FISH"]
    }
  ],
  "exclusion_criteria": [
    {
      "criterion_id": "EC_001",
      "type": "medication_history",
      "drug_class": "anthracycline",
      "operator": "never_administered"
    }
  ]
}
```

The Python eligibility engine evaluates each patient's Silver layer records against
this rule set and writes match results to DuckDB Gold.

### 4. Eligibility Matching Engine (Python + DuckDB)

```python
# eligibility/engine.py
import duckdb
import anthropic
from eligibility.parser import parse_criteria
from eligibility.models import MatchResult

def run_matching(db_path: str = "oncology.duckdb"):
    con = duckdb.connect(db_path)

    trials = con.execute("SELECT trial_id, criteria_text FROM silver.dim_trials").fetchall()
    patients = con.execute("SELECT * FROM silver.dim_patients").df()

    results = []
    for trial_id, criteria_text in trials:
        rules = parse_criteria(criteria_text)          # Claude API call
        for _, patient in patients.iterrows():
            patient_data = get_patient_clinical_data(con, patient["patient_id"])
            match = evaluate_patient(patient["patient_id"], trial_id, rules, patient_data)
            results.append(match)

    con.execute("""
        INSERT INTO gold.fact_trial_matches
        SELECT * FROM results_df
    """, {"results_df": results_to_df(results)})
```

### 5. Data Quality (Great Expectations)

Expectation suites gate every Silver → Gold promotion:

| Table | Key Expectations |
|---|---|
| `dim_patients` | DOB not null, age 0–120, sex in accepted values |
| `dim_diagnoses` | ICD-10 regex match, valid code lookup |
| `dim_labs` | Values within physiological bounds per LOINC code |
| `dim_medications` | RxNorm code not null, start_date before end_date |
| `fact_trial_matches` | match_score between 0.0–1.0, no orphan patient_ids |

GE checkpoint runs as a Prefect task between Silver dbt run and Gold promotion.
Failures halt downstream tasks and log to console.

### 6. CI/CD (GitHub Actions)

```yaml
# .github/workflows/dbt_ci.yml
on: [pull_request]
jobs:
  dbt-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: pip install dbt-duckdb great_expectations
      - run: dbt deps && dbt compile
      - run: dbt run --select bronze silver
      - run: dbt test --select bronze silver
      - run: great_expectations checkpoint run silver_promotion
```

---

## Repository Structure

```
oncology-trial-eligibility-pipeline/
│
├── flows/
│   ├── ingest_patient_data.py
│   ├── ingest_trial_registry.py
│   └── run_eligibility_matching.py
│
├── dbt/
│   ├── models/
│   │   ├── bronze/
│   │   ├── silver/
│   │   └── gold/
│   ├── tests/
│   │   └── icd10_format.sql
│   ├── macros/
│   └── dbt_project.yml
│
├── eligibility/
│   ├── parser.py               # Claude API → structured criteria JSON
│   ├── engine.py               # Patient × trial matching logic
│   ├── evaluators/
│   │   ├── lab_evaluator.py
│   │   ├── medication_evaluator.py
│   │   └── biomarker_evaluator.py
│   └── models.py               # MatchResult dataclass
│
├── data_quality/
│   ├── expectations/
│   │   ├── dim_patients.json
│   │   ├── dim_diagnoses.json
│   │   └── dim_labs.json
│   └── checkpoints/
│       └── silver_promotion_checkpoint.yml
│
├── synthetic_data/
│   ├── generate_patients.py    # Faker + OMOP schema → Parquet
│   ├── generate_trials.py      # Sample trial criteria text → JSON
│   └── seed_local.py
│
├── streamlit/
│   └── app.py                  # Cohort explorer — queries DuckDB directly
│
├── docker/
│   ├── docker-compose.yml      # Prefect server + worker
│   └── Dockerfile
│
├── tests/
│   ├── test_parser.py          # Claude API criteria parsing unit tests
│   ├── test_engine.py          # Matching logic tests
│   └── test_evaluators.py
│
├── .github/
│   └── workflows/
│       └── dbt_ci.yml
│
├── .env.example
├── requirements.txt
└── README.md
```

---

## Local Setup

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Anthropic API key

### 1. Clone and configure

```bash
git clone https://github.com/sajanshergill/oncology-trial-eligibility-pipeline.git
cd oncology-trial-eligibility-pipeline
cp .env.example .env
# Set: ANTHROPIC_API_KEY
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
# Key packages: dbt-duckdb, duckdb, prefect, great_expectations,
#               anthropic, streamlit, faker, pandas, pyarrow
```

### 3. Generate synthetic data

```bash
python synthetic_data/generate_patients.py --n 5000
python synthetic_data/generate_trials.py --n 50
```

### 4. Start Prefect (Docker)

```bash
docker-compose up -d
# Prefect UI at localhost:4200
```

### 5. Run dbt models

```bash
cd dbt
dbt deps
dbt run --select bronze
dbt test --select bronze
dbt run --select silver
dbt test --select silver
dbt run --select gold
```

### 6. Run eligibility matching

```bash
python flows/run_eligibility_matching.py
```

### 7. Launch dashboard

```bash
streamlit run streamlit/app.py
# Opens at localhost:8501
```

---

## Data Model

### `fact_trial_matches` (Gold — DuckDB)

| Column | Type | Description |
|---|---|---|
| `match_id` | VARCHAR | Surrogate key (patient_id \|\| trial_id) |
| `patient_id` | VARCHAR | FK → dim_patients |
| `trial_id` | VARCHAR | FK → dim_trials (NCT number) |
| `match_score` | DOUBLE | 0.0–1.0; proportion of inclusion criteria met |
| `matched_criteria` | JSON | List of criterion IDs patient satisfies |
| `disqualifiers` | JSON | Criterion IDs + reasons for non-match |
| `evaluated_at` | TIMESTAMP | When matching run executed |
| `trial_phase` | VARCHAR | Phase I / II / III / IV |
| `primary_indication` | VARCHAR | e.g., Non-Small Cell Lung Cancer |

---

## Design Decisions

**Why DuckDB instead of Snowflake?**
DuckDB is zero-infrastructure, runs entirely in-process, reads Parquet natively, and supports the same SQL dialect patterns used in Snowflake. For a portfolio project it removes cloud account dependencies while demonstrating identical data modeling skills. The dbt models are written to be trivially portable to Snowflake by changing one line in `profiles.yml`.

**Why Prefect instead of Airflow?**
Prefect runs locally without a separate metadata DB or web server infrastructure. Docker Compose brings up a full Prefect server + worker in two commands. The DAG patterns are conceptually identical to Airflow.

**Why Claude API for criteria parsing?**
Eligibility criteria are authored by clinical teams in natural language with no standard schema. Rule-based regex fails on edge cases. An LLM parse step with structured JSON output is both realistic and directly maps to the "AI-assisted tooling" signal in the JD.

**Why OMOP-adjacent schema?**
OMOP CDM is the de facto standard in real-world evidence oncology data — widely used by health systems, CROs, and companies like Flatiron. Modeling synthetic data in this shape signals immediate familiarity with production healthcare data patterns.

---

## Skills Demonstrated

| Skill | Where |
|---|---|
| SQL (analytical, window functions, CTEs) | dbt silver/gold models |
| Python | Eligibility engine, criteria parser, Prefect flows |
| ETL/ELT pipeline design | Bronze → Silver → Gold via Prefect + dbt |
| dbt (medallion architecture) | Full model suite with tests and macros |
| DuckDB | Primary storage and query engine |
| Data quality & validation | Great Expectations + dbt custom tests |
| CI/CD | GitHub Actions: dbt compile/test on PR |
| Docker | Local dev compose stack (Prefect) |
| Claude API (AI-assisted tooling) | Free-text criteria → structured JSON rules |
| Healthcare data standards | OMOP CDM schema, ICD-10, LOINC, RxNorm |
| Cross-functional communication | Dashboard designed for non-technical research teams |

---

## Author

**Sajan Singh Shergill**
MS Data Science — Pace University, Seidenberg School (May 2026)
[linkedin.com/in/sajanshergill](https://linkedin.com/in/sajanshergill) · [sajansshergill.github.io](https://sajansshergill.github.io) · sajansshergill@gmail.com
