"""
streamlit/app.py
-----------------
Oncology Trial Eligibility — Cohort Explorer
Queries DuckDB directly. No backend required.

Run: streamlit run streamlit/app.py
"""

import json
from pathlib import Path

import duckdb
import pandas as pd
import streamlit as st

DB_PATH = Path(__file__).parent.parent / "oncology.duckdb"

st.set_page_config(
    page_title="Oncology Trial Eligibility Explorer",
    page_icon="🧬",
    layout="wide"
)

# ── DB connection ─────────────────────────────────────────────────────────────

@st.cache_resource
def get_connection():
    return duckdb.connect(str(DB_PATH), read_only=True)


def query(sql: str, params=None) -> pd.DataFrame:
    con = get_connection()
    if params:
        return con.execute(sql, params).df()
    return con.execute(sql).df()


# ── Check if matching has been run ────────────────────────────────────────────

def matches_available() -> bool:
    try:
        n = query("SELECT COUNT(*) AS n FROM main_gold.fact_trial_matches WHERE match_id IS NOT NULL").iloc[0]["n"]
        return n > 0
    except Exception:
        return False


# ── Sidebar ───────────────────────────────────────────────────────────────────

st.sidebar.image("https://img.icons8.com/fluency/48/dna-helix.png", width=48)
st.sidebar.title("Filters")

try:
    trials_df = query("""
        SELECT nct_id || ' — ' || primary_indication AS label, trial_id
        FROM main_silver.dim_trials ORDER BY nct_id
    """)
    trial_options = ["All Trials"] + trials_df["label"].tolist()
    trial_map     = dict(zip(trials_df["label"], trials_df["trial_id"]))
except Exception:
    trial_options = ["All Trials"]
    trial_map     = {}

selected_trial = st.sidebar.selectbox("Clinical Trial", trial_options)

cancer_types = st.sidebar.multiselect(
    "Cancer Type",
    ["Breast", "Lung", "Colorectal", "Leukemia", "Lymphoma",
     "Myeloma", "Prostate", "Pancreatic", "Melanoma", "Renal"],
    default=[]
)

ecog_max = st.sidebar.slider("Max ECOG Status", 0, 4, 2)

min_score = st.sidebar.slider(
    "Min Match Score", 0.0, 1.0, 0.0, step=0.05,
    help="0 = any match attempted, 1.0 = all inclusion criteria met"
)

eligible_only = st.sidebar.checkbox("Fully Eligible Only", value=False)

# ── Header ────────────────────────────────────────────────────────────────────

st.title("🧬 Oncology Trial Eligibility Explorer")
st.caption("Patient cohort matching for oncology clinical trials — powered by DuckDB + Claude API")

# ── Pipeline status ───────────────────────────────────────────────────────────

if not matches_available():
    st.warning(
        "⚠️ No matching results found. Run the eligibility engine first:\n\n"
        "```bash\npython eligibility/engine.py --limit 100\n```",
        icon="⚠️"
    )
    st.stop()

# ── KPI cards ─────────────────────────────────────────────────────────────────

try:
    summary = query("SELECT * FROM main_gold.mart_cohort_summary WHERE trial_id IS NOT NULL")
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)

    total_patients = query("""
        SELECT COUNT(DISTINCT patient_id) AS n
        FROM main_gold.fact_trial_matches WHERE match_id IS NOT NULL
    """).iloc[0]["n"]

    total_eligible = query("""
        SELECT COUNT(DISTINCT patient_id) AS n
        FROM main_gold.fact_trial_matches
        WHERE is_fully_eligible = true
    """).iloc[0]["n"]

    avg_score = query("""
        SELECT ROUND(AVG(match_score), 3) AS s
        FROM main_gold.fact_trial_matches WHERE match_id IS NOT NULL
    """).iloc[0]["s"]

    kpi1.metric("Trials Active",      len(summary))
    kpi2.metric("Patients Evaluated", f"{total_patients:,}")
    kpi3.metric("Fully Eligible",     f"{total_eligible:,}")
    kpi4.metric("Avg Match Score",    f"{avg_score:.1%}")

    st.divider()
except Exception as e:
    st.error(f"Could not load KPIs: {e}")

# ── Trial summary table ───────────────────────────────────────────────────────

st.subheader("Trial Cohort Summary")

if not summary.empty:
    display_cols = ["nct_id", "primary_indication", "phase",
                    "patients_evaluated", "fully_eligible_count",
                    "eligibility_rate_pct", "avg_match_score"]
    available = [c for c in display_cols if c in summary.columns]
    st.dataframe(
        summary[available].rename(columns={
            "nct_id":                 "NCT ID",
            "primary_indication":     "Indication",
            "phase":                  "Phase",
            "patients_evaluated":     "Patients Evaluated",
            "fully_eligible_count":   "Fully Eligible",
            "eligibility_rate_pct":   "Eligibility Rate (%)",
            "avg_match_score":        "Avg Match Score",
        }),
        use_container_width=True,
        hide_index=True
    )

st.divider()

# ── Patient-level match explorer ──────────────────────────────────────────────

st.subheader("Patient Match Detail")

# Build filter conditions
conditions = ["match_id IS NOT NULL", f"ecog_status <= {ecog_max}",
              f"match_score >= {min_score}"]

if selected_trial != "All Trials" and selected_trial in trial_map:
    conditions.append(f"trial_id = '{trial_map[selected_trial]}'")

if cancer_types:
    cancer_list = ", ".join(f"'{c}'" for c in cancer_types)
    conditions.append(f"primary_cancer IN ({cancer_list})")

if eligible_only:
    conditions.append("is_fully_eligible = true")

where_clause = " AND ".join(conditions)

matches = query(f"""
    SELECT
        patient_id,
        nct_id,
        primary_indication,
        phase,
        primary_cancer,
        stage_at_dx,
        ecog_status,
        age_at_diagnosis,
        gender,
        ROUND(match_score, 3)        AS match_score,
        matched_criteria_count,
        disqualifier_count,
        is_fully_eligible,
        disqualifiers_json
    FROM main_gold.fact_trial_matches
    WHERE {where_clause}
    ORDER BY match_score DESC
    LIMIT 500
""")

st.write(f"Showing **{len(matches):,}** patient×trial pairs (max 500)")

if not matches.empty:
    display = matches.drop(columns=["disqualifiers_json"], errors="ignore")
    st.dataframe(
        display.rename(columns={
            "patient_id":             "Patient ID",
            "nct_id":                 "Trial",
            "primary_indication":     "Indication",
            "phase":                  "Phase",
            "primary_cancer":         "Cancer Type",
            "stage_at_dx":            "Stage",
            "ecog_status":            "ECOG",
            "age_at_diagnosis":       "Age at Dx",
            "gender":                 "Sex",
            "match_score":            "Match Score",
            "matched_criteria_count": "Criteria Met",
            "disqualifier_count":     "Disqualifiers",
            "is_fully_eligible":      "Fully Eligible",
        }),
        use_container_width=True,
        hide_index=True
    )

    # ── Patient drill-down ────────────────────────────────────────────────────
    st.divider()
    st.subheader("Patient Drill-Down")

    selected_pid = st.selectbox(
        "Select a patient to see match detail",
        matches["patient_id"].tolist()
    )

    if selected_pid:
        patient_matches = matches[matches["patient_id"] == selected_pid]

        col_a, col_b = st.columns(2)
        row = patient_matches.iloc[0]
        col_a.metric("Cancer Type", row["primary_cancer"])
        col_a.metric("Stage",       row["stage_at_dx"])
        col_b.metric("ECOG",        row["ecog_status"])
        col_b.metric("Age at Dx",   row["age_at_diagnosis"])

        st.write("**Trial matches for this patient:**")
        for _, m in patient_matches.iterrows():
            eligible_badge = "✅ Fully Eligible" if m["is_fully_eligible"] else "🟡 Partial"
            with st.expander(
                f"{m['nct_id']} — {m['primary_indication']} "
                f"| Score: {m['match_score']:.1%} | {eligible_badge}"
            ):
                st.metric("Match Score",   f"{m['match_score']:.1%}")
                st.metric("Criteria Met",  m["matched_criteria_count"])
                st.metric("Disqualifiers", m["disqualifier_count"])

                if m["disqualifier_count"] > 0 and m["disqualifiers_json"]:
                    try:
                        disqs = json.loads(m["disqualifiers_json"])
                        st.write("**Disqualifying criteria:**")
                        for d in disqs:
                            st.error(f"• {d['id']}: {d['reason']}")
                    except Exception:
                        pass

else:
    st.info("No patients match the current filters.")

# ── Footer ────────────────────────────────────────────────────────────────────

st.divider()
st.caption(
    "Sajan Singh Shergill · MS Data Science, Pace University · "
    "[linkedin.com/in/sajanshergill](https://linkedin.com/in/sajanshergill) · "
    "[sajansshergill.github.io](https://sajansshergill.github.io)"
)