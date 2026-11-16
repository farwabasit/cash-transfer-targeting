-- 1 row per household
-- raw file has 2 rows per hh (female + male respondent). checked: only the psych scores
-- differ between them, so keeping the female row is fine for household variables
with src as (
    select *
    from {{ ref('brz_kenya_uct') }}
    qualify row_number() over (partition by "SURVEYID" order by "FEMALERES" desc) = 1
)

select
    "SURVEYID"::varchar                          as household_id,
    'KEN'                                        as country,
    "VILLAGE"::varchar                           as village_id,
    case when "TREAT" = 1 then 'treatment'
         when "SPILLOVER" = 1 then 'spillover'
         when "PURECONTROL" = 1 then 'pure_control' end as arm,
    "TREAT"::int                                 as treated,
    -- transfer design, only for treated
    iff("TREAT" = 1, "TREATXLUMP" = 1, null)     as lump_sum,
    iff("TREAT" = 1, "TREATXLARGE" = 1, null)    as large_transfer,
    iff("TREAT" = 1, "TREATXFEMALEREC" = 1, null) as female_recipient,
    "B_HHSIZE"::int                             as hh_size_bl,
    "B_CHILDREN"::int                            as children_bl,
    "B_CHILDREN" > 0                             as has_children_bl,
    "B_AGE"::float                               as respondent_age_bl,
    "B_MARRIED" = 1                              as married_bl,
    "B_EDU"::float                               as respondent_education_years_bl,
    "HH_TOTALMEMBERS1"::int                      as hh_size_el,
    ("CONS_NONDURABLE_PPP_MISS0" = 1 or "PURECONTROL" = 1) as consumption_missing_bl  -- see kenya consumption model
from src
