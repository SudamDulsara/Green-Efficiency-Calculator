import os
import yaml
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from workflow import run_workflow
from auth_utils import login, signup, logout  # Firebase auth helpers

# Load environment variables
load_dotenv()

# --- Page config ---
st.set_page_config(
    page_title="Green Efficiency Calculator",
    page_icon="🔋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Authentication state ---
if "user" not in st.session_state:
    st.session_state.user = None
if "menu" not in st.session_state:
    st.session_state.menu = "Login"

# Sidebar menu
if st.session_state.user:
    menu = ["App", "Logout"]
else:
    menu = ["Login", "Sign Up"]

choice = st.sidebar.selectbox("Menu", menu, index=menu.index(st.session_state.menu))

# --- LOGIN PAGE ---
if choice == "Login":
    st.header("🔐 Welcome Back!")
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

# --- SIGNUP PAGE ---
elif choice == "Sign Up":
    st.header("📝 Create a New Account")
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

# --- MAIN APP ---
elif choice == "App":
    if not st.session_state.user:
        st.warning("Please login first.")
        st.stop()

    # Sidebar user info
    st.sidebar.write(f"Hello, {st.session_state.user['email'].split('@')[0]}!")

    st.title("🔋 Green Efficiency Assessment")

    # Load defaults
    defaults = yaml.safe_load(open("data/defaults.yaml", "r", encoding="utf-8"))
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
            tariff = st.number_input("Tariff (LKR/kWh)", min_value=0.0, value=float(tariff_default), step=1.0)
        with ct2:
            monthly_kwh = st.number_input("Monthly consumption (kWh)", min_value=0.0, value=320.0, step=1.0)

        submitted = st.form_submit_button("Run Analysis")

    if submitted:
        if not os.getenv("OPENAI_API_KEY"):
            st.error("OpenAI API key not found in environment (.env). Please add OPENAI_API_KEY.")
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

            st.subheader("Top 3 Quick Wins")
            cols = st.columns(3) if len(plan["quick_wins"]) >= 3 else st.columns(len(plan["quick_wins"]) or 1)
            for i, item in enumerate(plan["quick_wins"]):
                with cols[i % len(cols)]:
                    st.metric(
                        label=item["action"],
                        value=f'{item["LKR_saved_per_month"]:.0f} LKR/mo',
                        delta=f'{item["kWh_saved_per_month"]:.0f} kWh/mo'
                    )

            st.subheader("All Actions")
            df = pd.DataFrame(plan["all_actions"])
            cols_order = ["action","kWh_saved_per_month","LKR_saved_per_month","est_cost","payback_months",
                          "pct_kwh_reduction_used","notes","steps"]
            df = df[[c for c in cols_order if c in df.columns]]
            st.dataframe(df, use_container_width=True)

            st.info(f'Estimated total impact: {plan["totals"]["kWh_saved_per_month"]:.0f} kWh/mo '
                    f'(~ {plan["totals"]["LKR_saved_per_month"]:.0f} LKR/mo)')

            st.subheader("Action Plan")
            st.write(plan["plan_text"])
            st.download_button(
                label="Download Action Plan (.md)",
                data=plan["plan_text"],
                file_name="action_plan.md",
                mime="text/markdown"
            )

    # Logout button
    if st.button("Logout"):
        logout()
        st.session_state.user = None
        st.session_state.menu = "Login"
        st.rerun()
