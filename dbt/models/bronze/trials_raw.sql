select * from {{ source('bronze', 'trials_raw') }}
