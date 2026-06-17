select
    trial_id,
    nct_id,
    trial_title,
    primary_indication,
    phase,
    count(distinct patient_id) as patients_evaluated,
    sum(case when is_fully_eligible then 1 else 0 end) as fully_eligible_count,
    round(
        100.0 * sum(case when is_fully_eligible then 1 else 0 end)
        / nullif(count(distinct patient_id), 0),
        2
    ) as eligibility_rate_pct,
    round(avg(match_score), 4) as avg_match_score,
    max(evaluated_at) as latest_evaluated_at
from {{ ref('fact_trial_matches') }}
group by
    trial_id,
    nct_id,
    trial_title,
    primary_indication,
    phase
