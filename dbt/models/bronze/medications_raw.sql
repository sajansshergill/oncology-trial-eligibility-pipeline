select * from {{ source('bronze', 'medications_raw') }}
