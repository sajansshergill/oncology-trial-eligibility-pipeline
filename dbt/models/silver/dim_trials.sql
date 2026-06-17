select
    trial_id,
    nct_id,
    title,
    phase,
    primary_indication,
    sponsor,
    criteria_text,
    status,
    lower(status) = 'recruiting' as is_recruiting,
    cast(start_date as date) as start_date,
    cast(estimated_end_date as date) as estimated_end_date,
    cast(target_enrollment as integer) as target_enrollment,
    source_file,
    ingested_at,
    _source_file,
    _batch_id
from {{ ref('trials_raw') }}
where trial_id is not null
  and criteria_text is not null
