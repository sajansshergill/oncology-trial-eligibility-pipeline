select
    biomarker_id,
    patient_id,
    cancer_type,
    cast(test_date as date) as test_date,
    her2_status,
    er_status,
    pr_status,
    egfr_mutation,
    alk_rearrangement,
    pdl1_expression,
    kras_mutation,
    msi_status,
    tmb,
    source_file,
    ingested_at,
    _source_file,
    _batch_id
from {{ ref('biomarkers_raw') }}
where patient_id is not null
