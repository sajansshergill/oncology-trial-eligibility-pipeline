select * from {{ source('bronze', 'patients_raw') }}
