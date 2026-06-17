with medications as (
    select
        medication_id,
        patient_id,
        rxnorm_code,
        lower(trim(drug_name)) as drug_name,
        lower(trim(drug_class)) as drug_class,
        route,
        cast(line_of_therapy as integer) as line_of_therapy,
        cast(start_date as date) as start_date,
        cast(end_date as date) as end_date,
        lower(trim(discontinuation_reason)) as discontinuation_reason,
        source_file,
        ingested_at,
        _source_file,
        _batch_id
    from {{ ref('medications_raw') }}
    where patient_id is not null
      and rxnorm_code is not null
)

select
    *,
    drug_class = 'anthracycline' as is_prior_anthracycline,
    drug_class = 'checkpoint_inhibitor' as is_prior_immunotherapy,
    drug_class = 'egfr_inhibitor' as is_prior_egfr_inhibitor,
    drug_class = 'cdk4_6_inhibitor' as is_prior_cdk46_inhibitor,
    drug_name = 'osimertinib' as is_prior_osimertinib,
    drug_name = 'trastuzumab' as is_prior_trastuzumab
from medications
