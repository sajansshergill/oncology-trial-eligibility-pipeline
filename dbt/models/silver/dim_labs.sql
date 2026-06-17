with labs as (
    select
        lab_id,
        patient_id,
        loinc_code,
        lower(trim(lab_name)) as lab_name,
        cast(value as double) as value,
        unit,
        cast(lab_date as date) as lab_date,
        cast(normal_low as double) as normal_low,
        cast(normal_high as double) as normal_high,
        coalesce(
            cast(is_abnormal as boolean),
            cast(value as double) < cast(normal_low as double)
                or cast(value as double) > cast(normal_high as double)
        ) as is_abnormal,
        source_file,
        ingested_at,
        _source_file,
        _batch_id
    from {{ ref('labs_raw') }}
    where patient_id is not null
      and loinc_code is not null
)

select
    *,
    row_number() over (
        partition by patient_id, lab_name
        order by lab_date desc, lab_id
    ) as recency_rank
from labs
