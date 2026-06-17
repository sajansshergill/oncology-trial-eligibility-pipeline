with engine_output as (
    select * from gold.engine_output
),

patients as (
    select * from {{ ref('dim_patients') }}
),

trials as (
    select * from {{ ref('dim_trials') }}
)

select
    eo.match_id,
    eo.patient_id,
    eo.trial_id,
    coalesce(eo.nct_id, trials.nct_id) as nct_id,
    coalesce(eo.trial_title, trials.title) as trial_title,
    coalesce(eo.primary_indication, trials.primary_indication) as primary_indication,
    coalesce(eo.phase, trials.phase) as phase,
    patients.primary_cancer,
    patients.stage_at_dx,
    patients.ecog_status,
    patients.age_at_diagnosis,
    patients.gender,
    patients.race,
    patients.ethnicity,
    patients.state,
    patients.is_metastatic,
    cast(eo.match_score as double) as match_score,
    cast(eo.matched_criteria_count as integer) as matched_criteria_count,
    cast(eo.total_inclusion_criteria as integer) as total_inclusion_criteria,
    cast(eo.disqualifier_count as integer) as disqualifier_count,
    eo.matched_criteria_json,
    eo.disqualifiers_json,
    cast(eo.is_fully_eligible as boolean) as is_fully_eligible,
    cast(eo.evaluated_at as timestamp) as evaluated_at
from engine_output as eo
left join patients
    on eo.patient_id = patients.patient_id
left join trials
    on eo.trial_id = trials.trial_id
