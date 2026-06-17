with patients as (
    select * from {{ ref('patients_raw') }}
)

select
    patient_id,
    cast(birth_date as date) as birth_date,
    gender,
    race,
    ethnicity,
    state,
    zip_code,
    cast(ecog_status as integer) as ecog_status,
    smoking_status,
    primary_cancer,
    index_icd10,
    stage_at_dx,
    cast(diagnosis_date as date) as diagnosis_date,
    cast(is_metastatic as boolean) as is_metastatic,
    greatest(
        0,
        date_diff('year', cast(birth_date as date), cast(diagnosis_date as date))
    ) as age_at_diagnosis,
    greatest(
        0,
        date_diff('year', cast(birth_date as date), current_date)
    ) as age_at_index,
    source_file,
    ingested_at,
    _source_file,
    _batch_id
from patients
where patient_id is not null
