# oncology_codes.py
# Reference tables for realistic synthetic oncology data generation

ICD10_ONCOLOGY = [
    {"code": "C34.10", "description": "Non-small cell lung cancer, upper lobe", "category": "Lung"},
    {"code": "C34.11", "description": "Non-small cell lung cancer, upper lobe, right", "category": "Lung"},
    {"code": "C34.31", "description": "Non-small cell lung cancer, lower lobe, right", "category": "Lung"},
    {"code": "C50.911", "description": "Breast cancer, unspecified, right", "category": "Breast"},
    {"code": "C50.912", "description": "Breast cancer, unspecified, left", "category": "Breast"},
    {"code": "C18.9",  "description": "Colorectal cancer, unspecified", "category": "Colorectal"},
    {"code": "C18.2",  "description": "Colorectal cancer, ascending colon", "category": "Colorectal"},
    {"code": "C61",    "description": "Prostate cancer", "category": "Prostate"},
    {"code": "C25.9",  "description": "Pancreatic cancer, unspecified", "category": "Pancreatic"},
    {"code": "C43.9",  "description": "Melanoma, unspecified", "category": "Melanoma"},
    {"code": "C91.00", "description": "Acute lymphoblastic leukemia", "category": "Leukemia"},
    {"code": "C92.00", "description": "Acute myeloid leukemia", "category": "Leukemia"},
    {"code": "C85.10", "description": "Unspecified B-cell non-Hodgkin lymphoma", "category": "Lymphoma"},
    {"code": "C90.00", "description": "Multiple myeloma", "category": "Myeloma"},
    {"code": "C64.1",  "description": "Renal cell carcinoma, right kidney", "category": "Renal"},
]

LOINC_LABS = [
    {"code": "26464-8", "name": "platelet_count",       "unit": "10*9/L", "low": 50,  "normal_low": 150, "normal_high": 400,  "high": 800},
    {"code": "718-7",   "name": "hemoglobin",           "unit": "g/dL",   "low": 4.0, "normal_low": 11.5,"normal_high": 17.5, "high": 22.0},
    {"code": "2160-0",  "name": "creatinine",           "unit": "mg/dL",  "low": 0.3, "normal_low": 0.6, "normal_high": 1.2,  "high": 8.0},
    {"code": "1742-6",  "name": "alt",                  "unit": "U/L",    "low": 5,   "normal_low": 7,   "normal_high": 56,   "high": 500},
    {"code": "6768-6",  "name": "alkaline_phosphatase", "unit": "U/L",    "low": 20,  "normal_low": 44,  "normal_high": 147,  "high": 1000},
    {"code": "1975-2",  "name": "total_bilirubin",      "unit": "mg/dL",  "low": 0.1, "normal_low": 0.1, "normal_high": 1.2,  "high": 20.0},
    {"code": "2823-3",  "name": "potassium",            "unit": "mEq/L",  "low": 2.5, "normal_low": 3.5, "normal_high": 5.0,  "high": 7.0},
    {"code": "2951-2",  "name": "sodium",               "unit": "mEq/L",  "low": 120, "normal_low": 136, "normal_high": 145,  "high": 160},
    {"code": "33914-3", "name": "egfr",                 "unit": "mL/min", "low": 10,  "normal_low": 60,  "normal_high": 120,  "high": 120},
    {"code": "2276-4",  "name": "ferritin",             "unit": "ng/mL",  "low": 5,   "normal_low": 12,  "normal_high": 300,  "high": 2000},
]

RXNORM_MEDICATIONS = [
    {"code": "583214", "name": "carboplatin",     "class": "platinum_compound",         "route": "IV"},
    {"code": "309311", "name": "paclitaxel",      "class": "taxane",                    "route": "IV"},
    {"code": "583218", "name": "docetaxel",       "class": "taxane",                    "route": "IV"},
    {"code": "224905", "name": "doxorubicin",     "class": "anthracycline",             "route": "IV"},
    {"code": "583219", "name": "epirubicin",      "class": "anthracycline",             "route": "IV"},
    {"code": "583220", "name": "cyclophosphamide","class": "alkylating_agent",          "route": "IV"},
    {"code": "583221", "name": "trastuzumab",     "class": "monoclonal_antibody",       "route": "IV"},
    {"code": "583222", "name": "bevacizumab",     "class": "monoclonal_antibody",       "route": "IV"},
    {"code": "583223", "name": "pembrolizumab",   "class": "checkpoint_inhibitor",      "route": "IV"},
    {"code": "583224", "name": "nivolumab",       "class": "checkpoint_inhibitor",      "route": "IV"},
    {"code": "583225", "name": "erlotinib",       "class": "egfr_inhibitor",            "route": "oral"},
    {"code": "583226", "name": "osimertinib",     "class": "egfr_inhibitor",            "route": "oral"},
    {"code": "583227", "name": "imatinib",        "class": "tyrosine_kinase_inhibitor", "route": "oral"},
    {"code": "583228", "name": "palbociclib",     "class": "cdk4_6_inhibitor",          "route": "oral"},
    {"code": "583229", "name": "letrozole",       "class": "aromatase_inhibitor",       "route": "oral"},
]

BIOMARKER_PROFILES = {
    "Breast": [
        {"her2_status": "positive", "er_status": "positive",  "pr_status": "positive",  "weight": 0.30},
        {"her2_status": "negative", "er_status": "positive",  "pr_status": "positive",  "weight": 0.40},
        {"her2_status": "negative", "er_status": "negative",  "pr_status": "negative",  "weight": 0.20},
        {"her2_status": "positive", "er_status": "negative",  "pr_status": "negative",  "weight": 0.10},
    ],
    "Lung": [
        {"egfr_mutation": "exon19del", "alk_rearrangement": "negative", "pdl1_expression": "high",   "weight": 0.20},
        {"egfr_mutation": "L858R",     "alk_rearrangement": "negative", "pdl1_expression": "low",    "weight": 0.15},
        {"egfr_mutation": "wildtype",  "alk_rearrangement": "positive", "pdl1_expression": "low",    "weight": 0.10},
        {"egfr_mutation": "wildtype",  "alk_rearrangement": "negative", "pdl1_expression": "high",   "weight": 0.30},
        {"egfr_mutation": "wildtype",  "alk_rearrangement": "negative", "pdl1_expression": "low",    "weight": 0.25},
    ],
    "Colorectal": [
        {"kras_mutation": "wildtype", "msi_status": "MSI-H", "weight": 0.15},
        {"kras_mutation": "G12D",     "msi_status": "MSS",   "weight": 0.35},
        {"kras_mutation": "G12V",     "msi_status": "MSS",   "weight": 0.30},
        {"kras_mutation": "wildtype", "msi_status": "MSS",   "weight": 0.20},
    ],
    "default": [
        {"pdl1_expression": "high",   "tmb": "high",   "weight": 0.25},
        {"pdl1_expression": "low",    "tmb": "low",    "weight": 0.45},
        {"pdl1_expression": "medium", "tmb": "medium", "weight": 0.30},
    ]
}

SAMPLE_TRIAL_CRITERIA = [
    {
        "nct_id": "NCT04000001",
        "title": "Phase III Study of Pembrolizumab in Advanced NSCLC with High PD-L1 Expression",
        "phase": "Phase III", "indication": "Non-Small Cell Lung Cancer", "sponsor": "Synthetic Pharma Inc.",
        "criteria_text": (
            "Inclusion: Histologically confirmed NSCLC, stage IIIB or IV. "
            "ECOG performance status 0 or 1. PD-L1 expression >= 50% by IHC. "
            "No prior systemic therapy for metastatic disease. "
            "Adequate organ function: creatinine <= 1.5x ULN, ALT <= 2.5x ULN, "
            "platelet count >= 100 x 10^9/L, hemoglobin >= 9 g/dL. "
            "Exclusion: Prior treatment with anti-PD-1 or anti-PD-L1 antibodies. "
            "Active autoimmune disease requiring systemic treatment. "
            "EGFR sensitizing mutation or ALK rearrangement."
        )
    },
    {
        "nct_id": "NCT04000002",
        "title": "Phase II Study of Trastuzumab + Paclitaxel in HER2+ Breast Cancer",
        "phase": "Phase II", "indication": "Breast Cancer", "sponsor": "Synthetic Oncology Labs",
        "criteria_text": (
            "Inclusion: Histologically confirmed HER2-positive breast cancer confirmed by IHC 3+ or FISH. "
            "Stage II or III disease. ECOG performance status 0, 1, or 2. "
            "Adequate cardiac function: LVEF >= 50%. Platelet count >= 100 x 10^9/L. "
            "Hemoglobin >= 10 g/dL. Creatinine <= 1.5 mg/dL. "
            "Exclusion: Prior anthracycline therapy exceeding 360 mg/m2 doxorubicin equivalent. "
            "Active CNS metastases. Prior trastuzumab therapy."
        )
    },
    {
        "nct_id": "NCT04000003",
        "title": "Phase I Dose Escalation of Novel EGFR Inhibitor in EGFR-Mutant NSCLC",
        "phase": "Phase I", "indication": "Non-Small Cell Lung Cancer", "sponsor": "Biotech Research Co.",
        "criteria_text": (
            "Inclusion: NSCLC with confirmed EGFR sensitizing mutation (exon 19 deletion or L858R). "
            "Progression on prior EGFR-directed therapy. ECOG performance status 0 or 1. "
            "Age >= 18 years. Adequate renal function: eGFR >= 45 mL/min. "
            "Exclusion: Active brain metastases with neurological symptoms. "
            "Prior treatment with osimertinib. ALT or AST > 3x ULN."
        )
    },
    {
        "nct_id": "NCT04000004",
        "title": "Phase III Maintenance Therapy with Palbociclib in HR+ HER2- Breast Cancer",
        "phase": "Phase III", "indication": "Breast Cancer", "sponsor": "Synthetic Pharma Inc.",
        "criteria_text": (
            "Inclusion: Hormone receptor-positive, HER2-negative breast cancer. "
            "Stage IV or recurrent disease. Prior endocrine therapy required. "
            "ECOG performance status 0 or 1. "
            "Absolute neutrophil count >= 1.5 x 10^9/L. Platelet count >= 100 x 10^9/L. "
            "Exclusion: Prior CDK4/6 inhibitor therapy. Visceral crisis requiring chemotherapy. "
            "Known hypersensitivity to palbociclib."
        )
    },
    {
        "nct_id": "NCT04000005",
        "title": "Phase II Immunotherapy in MSI-H Colorectal Cancer",
        "phase": "Phase II", "indication": "Colorectal Cancer", "sponsor": "Immuno-Oncology Research Group",
        "criteria_text": (
            "Inclusion: Histologically confirmed colorectal adenocarcinoma. "
            "MSI-H or dMMR status confirmed by PCR or IHC. "
            "Stage IV disease. ECOG performance status 0, 1, or 2. "
            "At least one prior line of fluoropyrimidine-based chemotherapy. "
            "Adequate liver function: total bilirubin <= 1.5x ULN, ALT <= 3x ULN. "
            "Exclusion: Active inflammatory bowel disease. "
            "Prior immune checkpoint inhibitor therapy. KRAS or NRAS mutation."
        )
    },
]