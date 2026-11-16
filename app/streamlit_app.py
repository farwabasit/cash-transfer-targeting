"""Cash transfer targeting app.

    streamlit run app/streamlit_app.py
"""
import streamlit as st

st.set_page_config(page_title="Who Can Rise the Most", page_icon=":material/payments:", layout="wide")

pages = [
    st.Page("views/overview.py", title="Overview", icon=":material/home:", default=True),
    st.Page("views/who_gains.py", title="Who gains most", icon=":material/groups:"),
    st.Page("views/spending.py", title="Where the money went", icon=":material/shopping_basket:"),
    st.Page("views/budget.py", title="Budget trade-off", icon=":material/balance:"),
    st.Page("views/check.py", title="Check my households", icon=":material/upload_file:"),
    st.Page("views/own_programme.py", title="Analyse my own programme", icon=":material/insights:"),
    st.Page("views/how_built.py", title="How it's built", icon=":material/account_tree:"),
]
st.navigation(pages).run()

st.sidebar.caption(
    "Data: GiveDirectly randomised trials, Kenya 2011-12 (Haushofer & Shapiro) and "
    "Uganda 2019-22 (IDinsight), both CC0 on Harvard Dataverse. Pipeline: Snowflake + dbt."
)
