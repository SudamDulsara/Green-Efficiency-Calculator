import os, yaml, pandas as pd
import streamlit as st
from dotenv import load_dotenv
from workflow import run_workflow

load_dotenv()
st.set_page_config(page_title="Green Efficiency Calculator", page_icon="🔋", layout="centered")
st.title("🔋 Green Efficiency Assessment")

# Sidebar: API key & tariff default
api_key = st.sidebar.text_input("OpenAI API Key", type="password", value=os.getenv("OPENAI_API_KEY",""))
if api_key:
    os.environ["OPENAI_API_KEY"] = api_key

defaults = yaml.safe_load(open("data/defaults.yaml", "r", encoding="utf-8"))
tariff_default = float(defaults.get("tariff_LKR_per_kWh_default", 62))

with st.form("input_form"):
    st.subheader("Building & Devices")
    floor_area = st.number_input("Floor area (m²)", min_value=0.0, value=120.0, step=1.0)

    st.markdown("**Air Conditioning**")
    ac_count = st.number_input("Number of AC units", min_value=0, value=1, step=1)
    ac_watt = st.number_input("Typical watt per AC unit (W)", min_value=0, value=1200, step=50)
    ac_hours = st.number_input("AC hours per day", min_value=0.0, max_value=24.0, value=8.0, step=0.5)
    ac_star = st.slider("AC star rating", min_value=1, max_value=5, value=3)

    st.markdown("**Lighting**")
    bulbs = st.number_input("Number of bulbs", min_value=0, value=20, step=1)
    bulb_watt = st.number_input("Watt per bulb (W)", min_value=0, value=10, step=1)
    bulb_hours = st.number_input("Lighting hours per day", min_value=0.0, max_value=24.0, value=6.0, step=0.5)

    st.markdown("**Consumption & Tariff**")
    tariff = st.number_input("Tariff (LKR/kWh)", min_value=0.0, value=float(tariff_default), step=1.0)
    monthly_kwh = st.number_input("Monthly consumption (kWh)", min_value=0.0, value=320.0, step=1.0)

    submitted = st.form_submit_button("Run Analysis")

if submitted:
    if not os.getenv("OPENAI_API_KEY") and not api_key:
        st.error("Please provide your OpenAI API key in the sidebar.")
    else:
        payload = {
            "floor_area_m2": floor_area,
            "ac_units": [{"watt": ac_watt, "hours_per_day": ac_hours, "star_rating": ac_star}] * int(ac_count),
            "lighting": {"bulbs": bulbs, "watt_per_bulb": bulb_watt, "hours_per_day": bulb_hours},
            "tariff_LKR_per_kWh": tariff,
            "monthly_kWh": monthly_kwh,
        }
        with st.spinner("Analyzing…"):
            result = run_workflow(payload)

        plan = result["plan"]

        # Quick wins (top 3)
        st.subheader("Top 3 Quick Wins")
        cols = st.columns(3) if len(plan["quick_wins"]) >= 3 else st.columns(len(plan["quick_wins"]) or 1)
        for i, item in enumerate(plan["quick_wins"]):
            with cols[i % len(cols)]:
                st.metric(
                    label=item["action"],
                    value=f'{item["LKR_saved_per_month"]:.0f} LKR/mo',
                    delta=f'{item["kWh_saved_per_month"]:.0f} kWh/mo'
                )

        # Full table
        st.subheader("All Actions")
        df = pd.DataFrame(plan["all_actions"])
        # nicer column order
        cols_order = ["action","kWh_saved_per_month","LKR_saved_per_month","est_cost","payback_months","pct_kwh_reduction_used","notes","steps"]
        df = df[[c for c in cols_order if c in df.columns]]
        st.dataframe(df, width="stretch")

        # Totals
        st.info(f'Estimated total impact: **{plan["totals"]["kWh_saved_per_month"]:.0f} kWh/mo** '
                f'(~ **{plan["totals"]["LKR_saved_per_month"]:.0f} LKR/mo**).')

        # Action plan text + download
        st.subheader("Action Plan")
        st.write(plan["plan_text"])
        st.download_button(
            label="Download Action Plan (.md)",
            data=plan["plan_text"],
            file_name="action_plan.md",
            mime="text/markdown"
        )

        # Assumptions
        st.caption("This is an educational estimate. Validate with a certified energy auditor.")
