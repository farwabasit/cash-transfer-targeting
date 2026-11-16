-- effect of cash per country and household type (+ an ALL row per country)
-- simple comparison of endline means, treatment vs control (intention to treat)
-- the regression version (ANCOVA) and the causal model come from the python analysis step
{% set line = "(select monthly_ppp from " ~ ref('poverty_lines') ~ " where line_name = 'international_extreme')" %}

with hh as (
    select
        *,
        {{ line }} as poverty_line
    from {{ ref('gld_household_outcomes') }}
    where in_analysis
      and household_type is not null
      and consumption_pc_el_w is not null
),

stats as (
    select
        country,
        coalesce(household_type, 'ALL')                                        as household_type,
        count_if(treated = 1)                                                  as n_treatment,
        count_if(treated = 0)                                                  as n_control,
        avg(iff(treated = 1, consumption_pc_el_w, null))                       as mean_pc_treatment,
        avg(iff(treated = 0, consumption_pc_el_w, null))                       as mean_pc_control,
        variance(iff(treated = 1, consumption_pc_el_w, null))                  as var_treatment,
        variance(iff(treated = 0, consumption_pc_el_w, null))                  as var_control,
        avg(iff(treated = 1, hh_size_bl, null))                                as mean_hh_size_treatment,
        avg(iff(treated = 1, transfer_ppp, null))                              as mean_transfer_ppp,
        avg(iff(treated = 1, iff(consumption_pc_el_w < poverty_line, 1, 0), null)) as share_poor_treatment,
        avg(iff(treated = 0, iff(consumption_pc_el_w < poverty_line, 1, 0), null)) as share_poor_control,
        -- poverty gap: how far below the line on average (0 if above)
        avg(iff(treated = 1, greatest(0, (poverty_line - consumption_pc_el_w) / poverty_line), null)) as poverty_gap_treatment,
        avg(iff(treated = 0, greatest(0, (poverty_line - consumption_pc_el_w) / poverty_line), null)) as poverty_gap_control
    from hh
    group by grouping sets ((country, household_type), (country))
),

effects as (
    select
        s.*,
        mean_pc_treatment - mean_pc_control                                    as gain_pc_ppp,
        sqrt(var_treatment / n_treatment + var_control / n_control)            as gain_pc_se,
        (mean_pc_treatment - mean_pc_control) / nullif(mean_pc_control, 0)     as gain_pct
    from stats s
)

select
    e.country,
    e.household_type,
    coalesce(t.label, 'All households')                                        as household_type_label,
    e.n_treatment,
    e.n_control,
    e.mean_pc_control,
    e.mean_pc_treatment,
    e.gain_pc_ppp,
    e.gain_pc_se,
    e.gain_pc_ppp - 1.96 * e.gain_pc_se                                        as gain_pc_ci_low,
    e.gain_pc_ppp + 1.96 * e.gain_pc_se                                        as gain_pc_ci_high,
    e.gain_pct,
    e.gain_pc_se / nullif(e.mean_pc_control, 0)                                as gain_pct_se,
    e.mean_hh_size_treatment,
    e.mean_transfer_ppp,
    -- headline: extra household consumption per month for every $100 transferred
    100 * e.gain_pc_ppp * e.mean_hh_size_treatment / nullif(e.mean_transfer_ppp, 0) as monthly_gain_per_100_ppp,
    e.share_poor_control,
    e.share_poor_treatment,
    e.share_poor_control - e.share_poor_treatment                              as poverty_reduction_pp,
    iff(e.share_poor_control - e.share_poor_treatment > 0,
        e.mean_transfer_ppp / (e.share_poor_control - e.share_poor_treatment), null) as cost_per_household_lifted_ppp,
    e.poverty_gap_control,
    e.poverty_gap_treatment,
    e.poverty_gap_control - e.poverty_gap_treatment                            as poverty_gap_reduction,
    -- kenya consumption uses the paper's PPP base and almost everyone is far below the line,
    -- so the poverty line numbers are only really meaningful for uganda
    e.country = 'UGA'                                                          as poverty_line_comparable
from effects e
left join {{ ref('household_types') }} t on t.household_type = e.household_type
