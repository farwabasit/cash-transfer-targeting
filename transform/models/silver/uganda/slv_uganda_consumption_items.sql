{# one row per household / wave / item. item list is in seeds/uganda_consumption_items.csv
   baseline and endline questionnaires don't have the same items. each column is
   checked against the wave first and skipped if it's not there #}
{%- set waves = [
    {'wave': 'baseline_2019', 'year': 2019, 'rel': ref('brz_uganda_baseline')},
    {'wave': 'endline_2022',  'year': 2022, 'rel': ref('brz_uganda_endline')},
] -%}
{%- set items_ref = ref('uganda_consumption_items') -%}

{%- if execute -%}
    {%- set items = run_query(
        "select item, category, spend_group, recall, value_column, quantity_column, price_column, in_aggregate "
        ~ "from " ~ items_ref ~ " order by item").rows -%}
{%- else -%}
    {%- set items = [] -%}
{%- endif -%}

with unioned as (
{%- set selects = [] -%}
{%- for w in waves -%}
    {%- set cols = [] -%}
    {%- if execute -%}
        {%- for c in adapter.get_columns_in_relation(w.rel) -%}{%- do cols.append(c.name | upper) -%}{%- endfor -%}
    {%- endif -%}
    {%- for it in items -%}
        {%- set v = (it[4] or '') | upper -%}
        {%- set q = (it[5] or '') | upper -%}
        {%- set p = (it[6] or '') | upper -%}
        {%- set has_v, has_q, has_p = v in cols, (q != '' and q in cols), (p != '' and p in cols) -%}
        {%- if has_v or has_q -%}
            {%- set parts = [] -%}
            {%- if has_v -%}{%- do parts.append(nonneg('"' ~ v ~ '"')) -%}{%- endif -%}
            {%- if has_q and has_p -%}{%- do parts.append(nonneg('"' ~ q ~ '"') ~ ' * ' ~ nonneg('"' ~ p ~ '"')) -%}{%- endif -%}
            {%- set value_expr = 'coalesce(' ~ parts | join(', ') ~ ')' if parts | length > 1 else (parts[0] if parts else 'null::float') -%}
            {%- set sel -%}
    select
        "HHID_RAND"::varchar  as household_id,
        '{{ w.wave }}'        as wave,
        {{ w.year }}          as survey_year,
        '{{ it[0] }}'         as item,
        '{{ it[1] }}'         as category,
        '{{ it[2] }}'         as spend_group,
        '{{ it[3] }}'         as recall,
        {{ it[7] }}           as in_aggregate,
        {{ value_expr }}      as value_lcu
    from {{ w.rel }}
    {%- if 'BL_ONLY' in cols %}
    where "BL_ONLY" = 0   -- drop households not found at endline
    {%- endif %}
            {%- endset -%}
            {%- do selects.append(sel) -%}
        {%- endif -%}
    {%- endfor -%}
{%- endfor %}
{{ selects | join('\n    union all\n') if selects else 'select null::varchar as household_id, null::varchar as wave, null::number as survey_year, null::varchar as item, null::varchar as category, null::varchar as spend_group, null::varchar as recall, null::boolean as in_aggregate, null::float as value_lcu where false' }}
)

select
    u.household_id,
    u.wave,
    u.survey_year,
    u.item,
    u.category,
    u.spend_group,
    u.recall,
    u.in_aggregate,
    u.value_lcu,
    u.value_lcu * r.monthly_factor as monthly_value_lcu
from unioned u
join {{ ref('recall_periods') }} r on r.recall = u.recall
