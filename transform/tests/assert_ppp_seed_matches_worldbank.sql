-- the analysis uses PPP factors pinned in a seed (so results don't move when the world bank revises data).
-- this test warns when the live world bank value is more than 2% away from the pinned one
{{ config(severity='warn') }}

select
    s.country,
    s.year,
    s.lcu_per_intl_dollar        as pinned,
    w.ppp_lcu_per_intl_dollar    as world_bank_now,
    w.ppp_lcu_per_intl_dollar / s.lcu_per_intl_dollar - 1 as difference
from {{ ref('ppp_factors') }} s
left join {{ ref('slv_worldbank_prices') }} w
  on w.country = s.country and w.year = s.year
where w.ppp_lcu_per_intl_dollar is null
   or abs(w.ppp_lcu_per_intl_dollar / s.lcu_per_intl_dollar - 1) > 0.02
