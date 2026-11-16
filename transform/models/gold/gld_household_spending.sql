-- endline spending per person per month by spending group (PPP $), one row per household x group
-- uganda uses all items, also the ones left out of the consumption total (like home alcohol)
with uga_items as (
    select household_id, spend_group, sum(coalesce(monthly_value_lcu, 0)) as monthly_lcu
    from {{ ref('slv_uganda_consumption_items') }}
    where wave = 'endline_2022'
    group by 1, 2
),

uga as (
    select
        i.household_id,
        'UGA' as country,
        i.spend_group,
        i.monthly_lcu / c.hh_size / p.lcu_per_intl_dollar as spend_pc_ppp
    from uga_items i
    join {{ ref('slv_uganda_household_consumption') }} c
      on c.household_id = i.household_id and c.wave = 'endline_2022'
    join {{ ref('ppp_factors') }} p
      on p.country = 'UGA' and p.year = 2022
),

ken_el as (
    select * from {{ ref('slv_kenya_household_consumption') }}
    where wave = 'endline_2012'
),

ken as (
    select household_id, 'KEN' as country, spend_group, spend / hh_size as spend_pc_ppp
    from ken_el
    unpivot (spend for spend_group in (
        food_monthly_ppp, health_monthly_ppp, education_monthly_ppp, social_monthly_ppp))
    union all
    -- uganda has alcohol and tobacco together, so combine them for kenya too
    select household_id, 'KEN', 'alcohol_tobacco_monthly_ppp',
           (coalesce(alcohol_monthly_ppp, 0) + coalesce(tobacco_monthly_ppp, 0)) / hh_size
    from ken_el
)

select household_id, country, spend_group, spend_pc_ppp from uga
union all
select household_id, country, replace(lower(spend_group), '_monthly_ppp', ''), spend_pc_ppp from ken
