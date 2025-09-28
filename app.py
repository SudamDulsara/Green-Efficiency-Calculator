import os, yaml, pandas as pd
import streamlit as st
from typing import Any, Dict
import requests

API_URL = os.getenv("API_URL", "http://localhost:8000")
st.set_page_config(page_title="Green Efficiency Calculator", layout="centered")

st.title("Green Efficiency Calculator")

tab1, tab2 = st.tabs(["Classic (v1)", "Agentic (v2)"])

with tab1:
    st.subheader("One-shot workflow")
    with st.form("classic_form"):
        region = st.text_input("Region / Tariff Code (optional)")
        tariff = st.number_input("Tariff (LKR/kWh)", min_value=0.0, step=1.0, value=0.0)
        monthly_kwh = st.number_input("Monthly kWh", min_value=0.0, step=1.0, value=0.0)
        submit = st.form_submit_button("Run v1")
    if submit:
        payload = {"region": region or None, "tariff_LKR_per_kWh": tariff or None, "monthly_kWh": monthly_kwh or 0.0}
        res = requests.post(f"{API_URL}/run_workflow", json={"payload": payload}).json()
        st.json(res)

with tab2:
    st.subheader("Agentic flow with planner & tools")
    with st.form("agentic_form"):
        region2 = st.text_input("Region / Tariff Code")
        bill_text = st.text_area("Paste bill text (optional) — the agent will parse for kWh & tariff")
        monthly_kwh2 = st.number_input("Monthly kWh (optional if bill provided)", min_value=0.0, step=1.0, value=0.0)
        tariff2 = st.number_input("Tariff (LKR/kWh, optional if region provided)", min_value=0.0, step=1.0, value=0.0)
        agree = st.checkbox("I consent to anonymous logging for quality & safety checks", value=True)
        submit2 = st.form_submit_button("Run Agentic v2")
    if submit2:
        payload: Dict[str, Any] = {}
        if region2: payload["region"] = region2
        if bill_text: payload["bill_text"] = bill_text
        if monthly_kwh2: payload["monthly_kWh"] = monthly_kwh2
        if tariff2: payload["tariff_LKR_per_kWh"] = tariff2
        payload["consent_logging"] = bool(agree)

        res2 = requests.post(f"{API_URL}/agentic", json={"payload": payload}).json()
        st.write("**Trace ID:**", res2.get("trace_id"))
        st.json(res2)
