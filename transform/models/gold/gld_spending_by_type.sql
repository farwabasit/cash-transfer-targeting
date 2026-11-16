-- where did the money go? endline spending per person, treatment vs control, by type
with s as (
    select
        o.country,
        o.household_type,
        o.treated,
        sp.spend_group,
        sp.spend_pc_ppp
    from {{ ref('gld_household_spending') }} sp
    join {{ ref('gld_household_outcomes') }} o
      on o.household_id = sp.household_id and o.country = sp.country
    where o.in_analysis and o.household_type is not null
),

agg as (
    select
        country,
        coalesce(household_type, 'ALL')                       as household_type,
        spend_group,
        avg(iff(treated = 1, spend_pc_ppp, null))             as mean_spend_treatment,
        avg(iff(treated = 0, spend_pc_ppp, null))             as mean_spend_control
    from s
    group by grouping sets ((country, household_type, spend_group), (country, spend_group))
)

select
    *,
    mean_spend_treatment - mean_spend_control as extra_spend_pc_ppp
from agg
