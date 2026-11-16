{# BRONZE / SILVER / GOLD as schema names (dbt's default would make DEV_SILVER).
   on the ci target everything goes to CI_ schemas. branch builds never touch the tables the app reads #}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- elif target.name == 'ci' -%}
        CI_{{ custom_schema_name | trim | upper }}
    {%- else -%}
        {{ custom_schema_name | trim | upper }}
    {%- endif -%}
{%- endmacro %}
