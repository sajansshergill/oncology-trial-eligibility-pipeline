select * from {{ source('bronze', 'labs_raw') }}
