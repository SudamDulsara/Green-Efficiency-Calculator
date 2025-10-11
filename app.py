import os
import yaml
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from workflow import run_workflow
from utils.auth_utils import login, signup, logout

load_dotenv()

st.set_page_config(
    page_title="Green Efficiency Calculator",
    page_icon="🔋",
    layout="wide",
    initial_sidebar_state="expanded",
)

if "user" not in st.session_state:
    st.session_state.user = None
if "menu" not in st.session_state:
    st.session_state.menu = "Login"

if st.session_state.user:
    menu = ["App", "Logout"]
else:
    menu = ["Login", "Sign Up"]

choice = st.sidebar.selectbox("Menu", menu, index=menu.index(st.session_state.menu))

if choice == "Login":
    st.header(" Welcome Back!")
    st.write("Login to track energy efficiency & save LKR!")

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        user = login(email, password)
        if isinstance(user, dict):
            st.session_state.user = user
            st.success("Logged in successfully! Redirecting to app...")
            st.session_state.menu = "App"
            st.rerun()
        else:
            st.error(user)

elif choice == "Sign Up":
    st.header(" Create a New Account")
    st.write("Sign up to start tracking energy efficiency!")

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Sign Up"):
        user = signup(email, password)
        if isinstance(user, dict):
            st.success("Account created! Please login.")
            st.session_state.menu = "Login"
            st.rerun()
        else:
            st.error(user)

elif choice == "App":
    if not st.session_state.user:
        st.warning("Please login first.")
        st.stop()

    st.sidebar.write(f"Hello, {st.session_state.user['email'].split('@')[0]}!")
    if st.button("Logout"):
        logout()
        st.session_state.user = None
        st.session_state.menu = "Login"
        st.rerun()

    st.title("🔋 Green Efficiency Assessment")

    try:
        with open("data/defaults.yaml", "r", encoding="utf-8") as f:
            defaults = yaml.safe_load(f) or {}
    except Exception:
        defaults = {}
    tariff_default = float(defaults.get("tariff_LKR_per_kWh_default", 62))

    with st.form("input_form"):
        col_left, col_right = st.columns(2)

        with col_left:
            st.subheader("Building & Devices")
            floor_area = st.number_input("Floor area (m²)", min_value=0.0, value=120.0, step=1.0)

            st.write("**Air Conditioning**")
            ac_count = st.number_input("Number of AC units", min_value=0, value=1, step=1)
            ac_watt = st.number_input("Average watt per AC unit (W)", min_value=0, value=1200, step=50)
            ac_hours = st.number_input("AC hours per day", min_value=0.0, max_value=24.0, value=8.0, step=0.5)
            ac_star = st.slider("AC star rating", min_value=1, max_value=5, value=3)

        with col_right:
            st.subheader("Lighting")
            bulbs = st.number_input("Number of bulbs", min_value=0, value=20, step=1)
            bulb_watt = st.number_input("Average Watt per bulb (W)", min_value=0, value=10, step=1)
            bulb_hours = st.number_input("Lighting hours per day", min_value=0.0, max_value=24.0, value=6.0, step=0.5)

        st.subheader("Consumption & Tariff")
        ct1, ct2 = st.columns(2)
        with ct1:
            tariff = st.number_input(
                "Tariff (LKR/kWh)", min_value=0.0, value=float(tariff_default), step=1.0
            )
        with ct2:
            monthly_kwh = st.number_input("Monthly consumption (kWh)", min_value=0.0, value=320.0, step=1.0)

        with st.expander("🎯 Goals & Policy", expanded=True):
            c1, c2 = st.columns(2)
            with c1:
                target_budget = st.number_input(
                    "Target budget (LKR)",
                    min_value=0.0,
                    step=1000.0,
                    value=0.0,
                    help="Total capex you're willing to spend across all actions.",
                )
                payback_thr = st.number_input(
                    "Max payback (months)",
                    min_value=0,
                    step=1,
                    value=0,
                    help="Reject actions whose simple payback exceeds this.",
                )
            with c2:
                co2_goal = st.slider(
                    "CO₂ reduction goal (%)",
                    min_value=0,
                    max_value=100,
                    value=0,
                    help="Minimum monthly CO₂ reduction to aim for.",
                )
                max_disruption = st.selectbox(
                    "Max acceptable disruption",
                    options=["none", "low", "medium", "high"],
                    index=2,
                    help="Upper limit on disruption allowed for proposed actions.",
                )

        submitted = st.form_submit_button("Run Analysis")

    if submitted:
        if lighting_hours_invalid := (bulb_hours < 0 or bulb_hours > 24):
            st.error("Lighting hours must be between 0 and 24.")
        elif ac_hours < 0 or ac_hours > 24:
            st.error("AC hours must be between 0 and 24.")
        elif not os.getenv("OPENAI_API_KEY"):
            st.error("OpenAI API key not found in environment (.env). Please add OPENAI_API_KEY.")
        else:
            policy = {
                "target_budget_LKR": float(target_budget) if target_budget > 0 else None,
                "payback_threshold_months": int(payback_thr) if payback_thr > 0 else None,
                "co2_reduction_goal_pct": float(co2_goal) if co2_goal > 0 else None,
                "max_disruption": max_disruption,
            }

            payload = {
                "floor_area_m2": float(floor_area),
                "ac_units": [
                    {"watt": float(ac_watt), "hours_per_day": float(ac_hours), "star_rating": int(ac_star)}
                ]
                * int(ac_count),
                "lighting": {
                    "bulbs": int(bulbs),
                    "watt_per_bulb": float(bulb_watt),
                    "hours_per_day": float(bulb_hours),
                },
                "tariff_LKR_per_kWh": float(tariff),
                "monthly_kWh": float(monthly_kwh),
                "policy": policy,
            }

            with st.spinner("Analyzing…"):
                result = run_workflow(payload)

            plan = result.get("plan", {})
            totals = plan.get("totals", {}) or {}

            st.subheader("Top 3 Quick Wins")
            quick = plan.get("quick_wins", []) or []
            cols = st.columns(3) if len(quick) >= 3 else st.columns(len(quick) or 1)
            for i, item in enumerate(quick[:3]):
                with cols[i % len(cols)]:
                    st.metric(
                        label=item.get("action", f"Action {i+1}"),
                        value=f'{item.get("LKR_saved_per_month", 0):.0f} LKR/mo',
                        delta=f'{item.get("kWh_saved_per_month", 0):.0f} kWh/mo',
                    )

            st.subheader("All Actions")
            df = pd.DataFrame(plan.get("all_actions", []) or [])
            cols_order = [
                "action",
                "kWh_saved_per_month",
                "LKR_saved_per_month",
                "est_cost",
                "payback_months",
                "pct_kwh_reduction_used",
                "disruption",
                "co2_kg_saved_per_month",
                "notes",
                "steps",
            ]
            df = df[[c for c in cols_order if c in df.columns]]
            st.dataframe(df, use_container_width=True)

            total_kwh = totals.get("kWh_saved_per_month", 0.0) or 0.0
            total_lkr = totals.get("LKR_saved_per_month", 0.0) or 0.0
            total_co2 = totals.get("co2_kg_saved_per_month", 0.0) or 0.0

            st.info(
                f'Estimated total impact: {total_kwh:.0f} kWh/mo '
                f'(~ {total_lkr:.0f} LKR/mo) • {total_co2:.1f} kgCO₂/mo'
            )

            st.subheader("Policy enforcement")
            recs = result.get("recommendations", {}) or {}
            policy_report = recs.get("policy_report") or {}
            notes = policy_report.get("notes") or []

            b_cols = st.columns(4)
            effective_policy = plan.get("policy") or payload.get("policy") or {}
            b_cols[0].markdown(
                f"**Budget:** "
                f"{'∞' if (effective_policy.get('target_budget_LKR') in (None, 0)) else f'{int(effective_policy.get('target_budget_LKR')):,} LKR'}"
            )
            b_cols[1].markdown(
                f"**Max payback:** "
                f"{'∞' if (effective_policy.get('payback_threshold_months') in (None, 0)) else str(int(effective_policy.get('payback_threshold_months'))) + ' mo'}"
            )
            b_cols[2].markdown(
                f"**CO₂ goal:** "
                f"{'—' if (effective_policy.get('co2_reduction_goal_pct') in (None, 0)) else str(int(effective_policy.get('co2_reduction_goal_pct'))) + '%'}"
            )
            b_cols[3].markdown(f"**Max disruption:** {effective_policy.get('max_disruption', 'medium')}")

            if notes:
                with st.expander("What was enforced?"):
                    for n in notes:
                        st.write("- " + str(n))

            st.subheader("Action Plan")
            st.write(plan.get("plan_text", ""))

            st.download_button(
                label="Download Action Plan (.md)",
                data=plan.get("plan_text", ""),
                file_name="action_plan.md",
                mime="text/markdown",
            )