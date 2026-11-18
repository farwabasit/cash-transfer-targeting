-- one row per country and year with the three world bank price series side by side
select
    "COUNTRY"                                                                   as country,
    "YEAR"::int                                                                 as year,
    max(iff("INDICATOR" = 'PA.NUS.PRVT.PP', "VALUE", null))                     as ppp_lcu_per_intl_dollar,
    max(iff("INDICATOR" = 'PA.NUS.FCRF', "VALUE", null))                        as lcu_per_usd,
    max(iff("INDICATOR" = 'FP.CPI.TOTL', "VALUE", null))                        as cpi_2010_100,
    max("_LOADED_AT")                                                           as loaded_at
from {{ ref('brz_worldbank_indicators') }}
group by 1, 2
