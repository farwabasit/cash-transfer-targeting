-- households from the 6-country graduation programme (Banerjee et al. 2015)
-- graduation = an asset (often livestock), a food stipend for some months and training. not unconditional cash.
-- consumption is already monthly per person in 2014 USD PPP. bsl = baseline, end = ~2 years, fup = ~3 years
-- no household size per household in this file (the average per country is in the seed)
-- control = all households not offered the programme (ghana, honduras and peru also have control villages)
select
    g."ID"::varchar                      as household_id,
    c.country,
    c.country_name,
    g."TREATMENT"::int                   as treated,
    g."CTOTAL_PCMONTH_BSL"::float        as consumption_pc_bl,
    g."CTOTAL_PCMONTH_END"::float        as consumption_pc_end,
    g."CTOTAL_PCMONTH_FUP"::float        as consumption_pc_fup,
    g."ASSET_TOT_VALUE_BSL"::float       as asset_value_bl,
    g."ASSET_TOT_VALUE_END"::float       as asset_value_end,
    g."ASSET_TOT_VALUE_FUP"::float       as asset_value_fup
from {{ ref('brz_graduation_pooled_hh') }} g
join {{ ref('graduation_countries') }} c on c.country_code = g."COUNTRY"
