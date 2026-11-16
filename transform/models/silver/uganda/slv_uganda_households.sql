-- uganda households: assignment + baseline info + whether they were found at endline
with bl as (select * from {{ ref('brz_uganda_baseline') }}),
     el as (select * from {{ ref('brz_uganda_endline') }})

select
    bl."HHID_RAND"::varchar                         as household_id,
    'UGA'                                           as country,
    bl."TREAT"::int                                 as treated,          -- assignment, not actual receipt (ITT)
    bl."COHORT"::int                                as cohort,
    {{ nonneg('bl."HH_SIZE"') }}                    as hh_size_bl,
    iff(bl."HEAD_HH_SEX" = 1, true, false)          as female_head_bl,   -- 0 Male, 1 Female
    iff(bl."CHILDINHH" = 1, true, false)            as has_children_bl,
    iff(bl."EDU_LVL_H_R" between 0 and 7, bl."EDU_LVL_H_R"::int, null) as head_education_level_bl,
    el."BL_ONLY" = 0                                as surveyed_endline,
    iff(el."BL_ONLY" = 0, el."REC_TRANSFER" = 1, null) as reported_receiving_transfer
from bl
left join el on el."HHID_RAND" = bl."HHID_RAND"
