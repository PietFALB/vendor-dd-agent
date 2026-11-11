"""Web front end for the vendor due-diligence agent.  Run: streamlit run app.py"""
import os
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from agent.graph import build_graph

st.set_page_config(page_title="Vendor Due-Diligence Agent", page_icon="🔎", layout="wide")

# ---------------------------------------------------------------- password (only if one is set)

APP_PASSWORD = os.environ.get("APP_PASSWORD")
if APP_PASSWORD and not st.session_state.get("authenticated"):
    st.title("🔎 Vendor Due-Diligence Agent")
    entered = st.text_input("Password", type="password")
    if entered == APP_PASSWORD:
        st.session_state["authenticated"] = True
        st.rerun()
    elif entered:
        st.error("Wrong password.")
    st.stop()

STEPS = {
    "validate_input": "Validated the input",
    "resolve_entity": "Identified the company (GLEIF, KvK)",
    "screen_sanctions": "Screened sanctions lists (OpenSanctions)",
    "enhanced_review": "Enhanced review: agent researched news and guidance",
    "standard_review": "Standard review: agent researched news and guidance",
    "assess_risk": "Assessed the risk",
    "write_report": "Wrote the report",
    "check_report": "Checked the report",
    "save_report": "Saved the report",
}
BANNER = {"High": st.error, "Medium": st.warning, "Low": st.success}


@st.cache_resource
def get_graph():
    return build_graph()


# ---------------------------------------------------------------- header and sidebar

st.title("🔎 Vendor Due-Diligence Agent")
st.caption("Type a company name. The agent identifies it, screens it and its owners against sanctions lists, "
           "researches adverse media and writes a cited due-diligence report.")

with st.sidebar:
    st.header("How it works")
    st.markdown(
        "1. **Validate** the input\n"
        "2. **Resolve** the company in GLEIF and KvK\n"
        "3. **Screen** company, other names and parents against OpenSanctions\n"
        "4. **Route:** a sanctions hit means an enhanced review\n"
        "5. **Review:** a ReAct agent researches news and AML guidance\n"
        "6. **Assess** the risk; code sets a minimum rating\n"
        "7. **Write**, **check** and **save** the report"
    )
    st.divider()
    st.caption("Automated pre-screening to support, not replace, a compliance officer. Not legal advice. "
               "KvK data from the test environment; sanctions data from OpenSanctions (non-commercial).")

# ---------------------------------------------------------------- input

with st.form("check"):
    col1, col2 = st.columns([3, 1])
    name = col1.text_input("Company name", placeholder="e.g. Sberbank or ING Groep")
    kvk = col2.text_input("KvK number (optional)", placeholder="8 digits")
    submitted = st.form_submit_button("Run check", type="primary")

if submitted:
    if len(name.strip()) < 2:
        st.warning("Enter a company name.")
        st.stop()

    final, shown = None, 0
    with st.status(f"Checking {name.strip()} … this takes about a minute", expanded=True) as status:
        for state in get_graph().stream(
            {"company_name": name, "kvk_number": kvk or None, "errors": [], "trace": [], "check_attempts": 0},
            config={"run_name": "streamlit", "tags": ["streamlit"]},
            stream_mode="values",
        ):
            final = state
            trace = state.get("trace", [])
            for step in trace[shown:]:
                st.write(f"✓ {STEPS.get(step, step)}")
            shown = len(trace)
        status.update(label="Check complete", state="complete", expanded=False)
    st.session_state["result"] = final

# ---------------------------------------------------------------- result

result = st.session_state.get("result")
if result:
    if not result.get("valid", True):
        st.error(" ".join(result.get("errors", [])))
        st.stop()

    rating, rec = result.get("risk_rating"), result.get("recommendation")
    BANNER.get(rating, st.info)(f"### Risk rating: {rating}  ·  Recommendation: {rec}")
    if result.get("rating_floor_reason"):
        st.caption(f"Minimum set by rule: {result['rating_floor_reason']}")

    m = st.columns(4)
    m[0].metric("Sanctions hits", len(result.get("sanctions_hits", [])))
    m[1].metric("Adverse media findings", len(result.get("news", [])))
    m[2].metric("Red flags", len(result.get("red_flags", [])))
    m[3].metric("Data limitations", len(result.get("errors", [])))

    tab_report, tab_flags, tab_limits, tab_agent = st.tabs(
        ["📄 Report", "🚩 Red flags", "⚠️ Data limitations", "🤖 Agent steps"])

    with tab_report:
        report = result.get("report") or ""
        st.download_button("Download report (Markdown)", data=report,
                           file_name=Path(result.get("report_path") or "report.md").name, mime="text/markdown")
        st.markdown(report)

    with tab_flags:
        flags = result.get("red_flags", [])
        if flags:
            df = pd.DataFrame(flags)
            cols = [c for c in ["severity", "event_year", "flag", "category", "evidence", "evidence_source", "guidance_ref"]
                    if c in df.columns]
            st.dataframe(df[cols], hide_index=True, use_container_width=True)
        else:
            st.write("No red flags identified.")

    with tab_limits:
        errors = result.get("errors", [])
        if errors:
            for e in errors:
                st.markdown(f"- {e}")
        else:
            st.write("None recorded.")

    with tab_agent:
        st.markdown("**Route:** " + " → ".join(result.get("trace", [])))
        steps = result.get("agent_steps", [])
        if steps:
            st.markdown("**Searches the review agent chose itself:**")
            st.dataframe(pd.DataFrame([{"tool": s["tool"], "input": str(s["args"])} for s in steps]),
                         hide_index=True, use_container_width=True)
