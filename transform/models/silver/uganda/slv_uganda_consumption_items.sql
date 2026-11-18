-- one row per household / wave / item. the item list is in seeds/uganda_consumption_items.csv
-- baseline and endline don't have the same items. instead of checking columns with jinja, every survey row
-- is turned into (column name, value) pairs with object_construct_keep_null(*) + flatten and joined to the
-- item list. a column that isn't in a wave just has no pairs. it drops out by itself.
with surveys as (
    select 'baseline_2019' as wave, 2019 as survey_year, "HHID_RAND"::varchar as household_id,
           object_construct_keep_null(*) as answers
    from {{ ref('brz_uganda_baseline') }}
    union all
    select 'endline_2022', 2022, "HHID_RAND"::varchar, object_construct_keep_null(*)
    from {{ ref('brz_uganda_endline') }}
    where "BL_ONLY" = 0   -- drop households not found at endline
),

items as (
    select
        item, category, spend_group, recall, in_aggregate,
        upper(value_column)    as value_column,
        upper(quantity_column) as quantity_column,
        upper(price_column)    as price_column
    from {{ ref('uganda_consumption_items') }}
),

answers as (
    select s.household_id, s.wave, s.survey_year, f.key as column_name, f.value::float as answer
    from surveys s,
         lateral flatten(input => s.answers) f
),

per_item as (
    select
        a.household_id, a.wave, a.survey_year,
        i.item, i.category, i.spend_group, i.recall, i.in_aggregate,
        max(iff(a.column_name = i.value_column, {{ nonneg('a.answer') }}, null))    as reported_value,
        max(iff(a.column_name = i.quantity_column, {{ nonneg('a.answer') }}, null)) as quantity,
        max(iff(a.column_name = i.price_column, {{ nonneg('a.answer') }}, null))    as unit_price,
        -- the item only exists in this wave if its value or quantity column is there
        count_if(a.column_name in (i.value_column, i.quantity_column))              as item_columns
    from answers a
    join items i
      on a.column_name in (i.value_column, i.quantity_column, i.price_column)
    group by all
)

select
    p.household_id,
    p.wave,
    p.survey_year,
    p.item,
    p.category,
    p.spend_group,
    p.recall,
    p.in_aggregate,
    -- food: the reported total if there is one, otherwise quantity x unit price
    coalesce(p.reported_value, p.quantity * p.unit_price)  as value_lcu,
    coalesce(p.reported_value, p.quantity * p.unit_price) * r.monthly_factor as monthly_value_lcu
from per_item p
join {{ ref('recall_periods') }} r on r.recall = p.recall
where p.item_columns > 0
