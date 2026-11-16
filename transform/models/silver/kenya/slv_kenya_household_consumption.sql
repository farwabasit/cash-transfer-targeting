-- kenya consumption per household and wave, same shape as uganda
-- values are already monthly PPP $ in the file (0 = baseline, 1 = endline)
-- TODO: check which PPP year the paper used before comparing with uganda
{%- set groups = {
    'food': 'CONS_ALLFOOD_PPP_M',
    'alcohol': 'CONS_ALCOHOL_PPP_M',
    'tobacco': 'CONS_TOBACCO_PPP_M',
    'health': 'CONS_MED_TOTAL_PPP_M',
    'education': 'CONS_ED_PPP_M',
    'social': 'CONS_SOCIAL_PPP_M',
} %}

with src as (
    select *
    from {{ ref('brz_kenya_uct') }}
    qualify row_number() over (partition by "SURVEYID" order by "FEMALERES" desc) = 1
),

waves as (
{%- for suffix, wave, year in [('0', 'baseline_2011', 2011), ('1', 'endline_2012', 2012)] %}
    select
        "SURVEYID"::varchar                          as household_id,
        '{{ wave }}'                                 as wave,
        {{ year }}                                   as survey_year,
        {%- if suffix == '0' %}
        "B_HHSIZE"::float                            as hh_size,
        -- pure control had no baseline survey but the file has 0 there. treat as missing
        ("CONS_NONDURABLE_PPP_MISS0" = 1 or "PURECONTROL" = 1) as is_missing,
        {%- else %}
        coalesce("HH_TOTALMEMBERS1", "B_HHSIZE")::float as hh_size,
        false                                        as is_missing,
        {%- endif %}
        "CONS_NONDURABLE_PPP{{ suffix }}"::float     as total_monthly_ppp
        {%- for g, col in groups.items() %},
        "{{ col }}{{ suffix }}"::float               as {{ g }}_monthly_ppp
        {%- endfor %}
    from src
    {% if not loop.last %}union all{% endif %}
{%- endfor %}
)

select
    household_id,
    'KEN'                                            as country,
    wave,
    survey_year,
    hh_size,
    iff(is_missing, null, total_monthly_ppp)         as total_monthly_ppp,
    iff(is_missing, null, total_monthly_ppp / hh_size) as consumption_pc_ppp,
    iff(is_missing, null, food_monthly_ppp / nullif(total_monthly_ppp, 0)) as food_share
    {%- for g in groups %},
    iff(is_missing, null, {{ g }}_monthly_ppp)       as {{ g }}_monthly_ppp
    {%- endfor %}
from waves
