{# Survey answers use negative codes for "don't know" / "refused" (e.g. -998). Treat them as missing. #}
{% macro nonneg(column) -%}
    iff({{ column }} >= 0, {{ column }}::float, null)
{%- endmacro %}
