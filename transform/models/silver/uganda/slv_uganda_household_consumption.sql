-- monthly consumption per household and per person (UGX + PPP $)
-- same logic as my python prototype, scripts/compare_with_prototype.py checks they match
with items as (
    select * from {{ ref('slv_uganda_consumption_items') }}
    where in_aggregate
),

totals as (
    select
        household_id,
        wave,
        survey_year,
        coalesce(sum(iff(category in ('food_home', 'food_away'), monthly_value_lcu, 0)), 0) as food_monthly_lcu,
        coalesce(sum(iff(category = 'nonfood', monthly_value_lcu, 0)), 0)                   as nonfood_monthly_lcu
    from items
    group by 1, 2, 3
),

sizes as (
    select "HHID_RAND"::varchar as household_id, 'baseline_2019' as wave, {{ nonneg('"HH_SIZE"') }} as hh_size
    from {{ ref('brz_uganda_baseline') }}
    union all
    select "HHID_RAND"::varchar, 'endline_2022', {{ nonneg('"HH_SIZE"') }}
    from {{ ref('brz_uganda_endline') }}
    where "BL_ONLY" = 0
),

winsorised as (
    select
        t.*,
        food_monthly_lcu + nonfood_monthly_lcu as total_monthly_lcu,
        -- winsorise top 1% per wave
        -- NOTE: this is on the hh total, a few 1-person households are still very high per person
        percentile_cont(0.99) within group (order by food_monthly_lcu + nonfood_monthly_lcu)
            over (partition by t.wave) as total_cap_lcu
    from totals t
)

select
    w.household_id,
    'UGA'                                                    as country,
    w.wave,
    w.survey_year,
    s.hh_size,
    w.food_monthly_lcu,
    w.nonfood_monthly_lcu,
    w.total_monthly_lcu,
    least(w.total_monthly_lcu, w.total_cap_lcu)              as total_monthly_lcu_w,
    least(w.total_monthly_lcu, w.total_cap_lcu) / s.hh_size  as consumption_pc_lcu,
    least(w.total_monthly_lcu, w.total_cap_lcu) / s.hh_size
        / p.lcu_per_intl_dollar                              as consumption_pc_ppp,
    w.food_monthly_lcu / nullif(w.total_monthly_lcu, 0)      as food_share
from winsorised w
join sizes s
  on s.household_id = w.household_id and s.wave = w.wave
join {{ ref('ppp_factors') }} p
  on p.country = 'UGA' and p.year = w.survey_year
