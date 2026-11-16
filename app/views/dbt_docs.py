from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

st.title("Data Catalogue")
st.markdown(
    "The dbt documentation of the pipeline: every model, column, test and source, with the **lineage graph** "
    "(click the blue round button at the bottom right) showing how raw survey files flow into the results."
)

docs = Path(__file__).resolve().parents[1] / "static" / "dbt_docs.html"
if not docs.exists():
    st.error("Docs not built yet. Run: python scripts/build_docs.py")
    st.stop()

html = docs.read_text(encoding="utf-8")
st.download_button("Download the docs to open in a full browser tab", html, "dbt_docs.html", "text/html")
components.html(html, height=850, scrolling=True)
