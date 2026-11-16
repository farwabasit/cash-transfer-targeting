-- pakistan in the same shape as the other countries, but only 2 types (no household size in the data):
-- poorer half / less poor half of baseline consumption per person. top 1% capped like the others
with hh as (
    select * from {{ ref('slv_pakistan_households') }}
    where consumption_pc_bl is not null
),

caps as (
    select
        percentile_cont(0.99) within group (order by consumption_pc_bl)  as cap_bl,
        percentile_cont(0.99) within group (order by consumption_pc_end) as cap_end,
        percentile_cont(0.99) within group (order by consumption_pc_fup) as cap_fup
    from hh
),

capped as (
    select
        hh.*,
        least(consumption_pc_bl, cap_bl)   as consumption_pc_bl_w,
        least(consumption_pc_end, cap_end) as consumption_pc_end_w,
        least(consumption_pc_fup, cap_fup) as consumption_pc_fup_w
    from hh cross join caps
)

select
    *,
    median(consumption_pc_bl_w) over ()                                        as median_consumption_pc_bl,
    iff(consumption_pc_bl_w < median(consumption_pc_bl_w) over (), 'poorer', 'less_poor') as poverty_group
from capped
