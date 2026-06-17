select *
from {{ ref('dim_diagnoses') }}
where not regexp_matches(icd10_code, '^[A-Z][0-9][0-9A-Z](\.[0-9A-Z]{1,4})?$')
