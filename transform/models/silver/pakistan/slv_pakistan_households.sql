-- pakistan households from the 6-country graduation data (country code 5)
-- graduation = an asset (livestock), a food stipend for some months and training. not unconditional cash.
-- consumption is already monthly per person in 2014 USD PPP. bsl = baseline, end = ~2 years, fup = ~3 years
-- no household size per household in this file
select
    "ID"::varchar                        as household_id,
    'PAK'                                as country,
    "TREATMENT"::int                     as treated,
    "CTOTAL_PCMONTH_BSL"::float          as consumption_pc_bl,
    "CTOTAL_PCMONTH_END"::float          as consumption_pc_end,
    "CTOTAL_PCMONTH_FUP"::float          as consumption_pc_fup,
    "ASSET_TOT_VALUE_BSL"::float         as asset_value_bl,
    "ASSET_TOT_VALUE_END"::float         as asset_value_end,
    "ASSET_TOT_VALUE_FUP"::float         as asset_value_fup
from {{ ref('brz_graduation_pooled_hh') }}
where "COUNTRY" = 5
