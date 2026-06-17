select
    diagnosis_id,
    patient_id,
    upper(trim(icd10_code)) as icd10_code,
    cast(diagnosis_date as date) as diagnosis_date,
    lower(trim(diagnosis_type)) as diagnosis_type,
    source_file,
    ingested_at,
    _source_file,
    _batch_id
from {{ ref('diagnoses_raw') }}
where patient_id is not null
  and icd10_code is not null
