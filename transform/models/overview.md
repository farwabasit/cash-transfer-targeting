{% docs __overview__ %}
# Who Can Rise the Most

Data pipeline behind the app [cash-transfer-targeting.streamlit.app](https://cash-transfer-targeting.streamlit.app).

It turns raw survey files from randomised trials into tested household tables:
GiveDirectly cash transfers in **Kenya** (2011-12) and **Uganda** (2019-22). Also the graduation programme in
**6 countries** (Ethiopia, Ghana, Honduras, India, Pakistan, Peru).

## Layers
- **raw**: survey files loaded by a Python loader (each file once, new columns added when a new wave has them)
- **bronze**: views on the raw tables
- **silver**: one clean row per household (Kenya had 2 rows per household, Uganda's consumption is rebuilt from about 100 survey items)
- **gold**: household types, effects per type, spending, the graduation countries

## How to read it
Open a model on the left to see its columns, tests and SQL. The blue button at the bottom right opens the
**lineage graph**: how every table is built from the ones before it.
{% enddocs %}
