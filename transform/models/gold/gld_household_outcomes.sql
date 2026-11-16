-- one row per household, both countries
-- has the household type, baseline + endline consumption per person and the transfer size
-- kenya: control = spillover households (pure control villages had no baseline survey)
-- uganda: control = cohorts 17-20, only households found at endline
with transfers as (
    select country, transfer_size, amount_ppp from {{ ref('transfer_amounts') }}
),

kenya as (
    select
        h.household_id,
        h.country,
        h.arm,
        h.treated,
        h.hh_size_bl::float                 as hh_size_bl,
        bl.consumption_pc_ppp               as consumption_pc_bl,
        el.consumption_pc_ppp               as consumption_pc_el,
        h.arm in ('treatment', 'spillover') and not h.consumption_missing_bl as in_analysis,
        iff(h.treated = 1, iff(h.large_transfer, 'large', 'small'), null) as transfer_size
    from {{ ref('slv_kenya_households') }} h
    left join {{ ref('slv_kenya_household_consumption') }} bl
        on bl.household_id = h.household_id and bl.wave = 'baseline_2011'
    left join {{ ref('slv_kenya_household_consumption') }} el
        on el.household_id = h.household_id and el.wave = 'endline_2012'
),

uganda as (
    select
        h.household_id,
        h.country,
        iff(h.treated = 1, 'treatment', 'control') as arm,
        h.treated,
        h.hh_size_bl,
        bl.consumption_pc_ppp               as consumption_pc_bl,
        el.consumption_pc_ppp               as consumption_pc_el,
        h.surveyed_endline and bl.consumption_pc_ppp is not null as in_analysis,
        iff(h.treated = 1, 'standard', null) as transfer_size
    from {{ ref('slv_uganda_households') }} h
    left join {{ ref('slv_uganda_household_consumption') }} bl
        on bl.household_id = h.household_id and bl.wave = 'baseline_2019'
    left join {{ ref('slv_uganda_household_consumption') }} el
        on el.household_id = h.household_id and el.wave = 'endline_2022'
),

both_countries as (
    select * from kenya
    union all
    select * from uganda
),

-- per person outliers: cap at p99 within country (silver only capped the household total)
caps as (
    select
        country,
        percentile_cont(0.99) within group (order by consumption_pc_bl) as cap_bl,
        percentile_cont(0.99) within group (order by consumption_pc_el) as cap_el
    from both_countries
    where in_analysis
    group by country
),

capped as (
    select
        b.*,
        least(b.consumption_pc_bl, c.cap_bl) as consumption_pc_bl_w,
        least(b.consumption_pc_el, c.cap_el) as consumption_pc_el_w
    from both_countries b
    join caps c using (country)
),

-- medians for the types, within each country (relative, not absolute)
medians as (
    select
        country,
        median(consumption_pc_bl_w) as median_consumption_pc_bl,
        median(hh_size_bl)          as median_hh_size_bl
    from capped
    where in_analysis
    group by country
),

typed as (
    select
        c.*,
        m.median_consumption_pc_bl,
        m.median_hh_size_bl,
        case
            when not c.in_analysis or c.consumption_pc_bl_w is null or c.hh_size_bl is null then null
            when c.consumption_pc_bl_w <  m.median_consumption_pc_bl and c.hh_size_bl <  m.median_hh_size_bl then 'A'
            when c.consumption_pc_bl_w <  m.median_consumption_pc_bl then 'B'
            when c.hh_size_bl < m.median_hh_size_bl then 'C'
            else 'D'
        end as household_type
    from capped c
    join medians m using (country)
)

select
    t.household_id,
    t.country,
    t.arm,
    t.treated,
    t.in_analysis,
    t.household_type,
    ht.label                                    as household_type_label,
    t.hh_size_bl,
    t.consumption_pc_bl,
    t.consumption_pc_el,
    t.consumption_pc_bl_w,
    t.consumption_pc_el_w,
    t.median_consumption_pc_bl,
    t.median_hh_size_bl,
    t.transfer_size,
    tr.amount_ppp::float                        as transfer_ppp
from typed t
left join {{ ref('household_types') }} ht on ht.household_type = t.household_type
left join transfers tr on tr.country = t.country and tr.transfer_size = t.transfer_size
