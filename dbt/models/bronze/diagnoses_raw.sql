select * from {{ source('bronze', 'diagnoses_raw') }}
