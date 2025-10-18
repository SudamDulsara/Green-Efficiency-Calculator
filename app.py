import os
import yaml
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
import re, html, urllib.parse as ul


from workflow import run_workflow
from utils.auth_utils import login, signup, logout
from utils.autofix import AutoFixContext
from utils.validation import validate_actions_report

load_dotenv()

st.set_page_config(
    page_title="Green Efficiency Calculator",
    page_icon="🔋",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    * { font-family: 'Inter', sans-serif; }

    #MainMenu, footer, header { visibility: hidden; }

    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%);
    }

    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1400px;
    }

    .energy-card {
        background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
        padding: 2rem;
        border-radius: 16px;
        border: 1px solid #475569;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
    }

    .main-header {
        background: linear-gradient(135deg, #16a34a 0%, #22c55e 50%, #16a34a 100%);
        padding: 3rem 2rem;
        border-radius: 20px;
        color: white;
        margin-bottom: 2rem;
        box-shadow: 0 8px 16px rgba(34, 197, 94, 0.3);
        position: relative;
        overflow: hidden;
    }
    .main-header::before {
        content: '';
        position: absolute; top: -50%; right: -50%;
        width: 200%; height: 200%;
        background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
        animation: pulse 4s ease-in-out infinite;
    }
    @keyframes pulse { 0%,100% {transform:scale(1);opacity:.5} 50% {transform:scale(1.1);opacity:.8} }
    .main-header h1 { color: white !important; font-size: 2.5rem; font-weight: 700; margin-bottom: .5rem; position: relative; z-index: 1; }
    .main-header p { color: rgba(255,255,255,0.95); font-size: 1.1rem; position: relative; z-index: 1; }

    .section-title {
        color: #22c55e;
        font-size: 1.75rem;
        font-weight: 700;
        margin: 2rem 0 1rem 0;
        padding-bottom: 0.75rem;
        border-bottom: 3px solid #22c55e;
    }
    .subsection-title {
        color: #86efac;
        font-size: 1.25rem;
        font-weight: 600;
        margin: 1.5rem 0 1rem 0;
        padding-left: 1rem;
        border-left: 4px solid #22c55e;
    }

    .metric-card {
        background: linear-gradient(135deg, #16a34a 0%, #22c55e 100%);
        padding: 1.5rem; border-radius: 12px; text-align: center;
        box-shadow: 0 4px 12px rgba(34,197,94,.4);
        transition: transform .3s ease, box-shadow .3s ease;
        border: 1px solid rgba(255,255,255,.1);
    }
    .metric-card:hover { transform: translateY(-5px); box-shadow: 0 8px 20px rgba(34,197,94,.6); }
    .metric-value { font-size: 2.25rem; font-weight: 700; color: white; margin-bottom: .25rem; }
    .metric-label { color: rgba(255,255,255,.9); font-size: .875rem; font-weight: 500; text-transform: uppercase; letter-spacing: .05em; }
    .metric-sublabel { color: rgba(255,255,255,.7); font-size: .75rem; margin-top: .25rem; }

    .stNumberInput > div > div > input,
    .stTextInput > div > div > input {
        background-color: #334155 !important;
        border: 2px solid #475569 !important;
        border-radius: 8px !important;
        color: #f1f5f9 !important;
        padding: 0.75rem !important;
        transition: all 0.3s ease;
    }
    .stNumberInput > div > div > input:focus,
    .stTextInput > div > div > input:focus {
        border-color: #22c55e !important;
        box-shadow: 0 0 0 3px rgba(34,197,94,.2) !important;
        background-color: #1e293b !important;
    }
    .stNumberInput label, .stTextInput label, .stSelectbox label, .stSlider label {
        color: #f1f5f9 !important; font-weight: 500 !important; font-size: .95rem !important;
    }
    .stSelectbox > div > div {
        background-color: #334155 !important; border: 2px solid #475569 !important; border-radius: 8px !important; color: #f1f5f9 !important;
    }
    .stSelectbox > div > div:focus-within {
        border-color: #22c55e !important; box-shadow: 0 0 0 3px rgba(34,197,94,.2) !important;
    }
    .stSlider > div > div > div { background-color: #475569 !important; }
    .stSlider > div > div > div > div { background-color: #22c55e !important; }

    .stButton > button, .stFormSubmitButton > button {
        background: linear-gradient(135deg, #16a34a 0%, #22c55e 100%) !important;
        color: white !important; border: none !important; border-radius: 12px !important;
        padding: 0.9rem 2rem !important; font-weight: 700 !important; font-size: 1rem !important;
        transition: all 0.3s ease !important; box-shadow: 0 6px 16px rgba(34,197,94,.4) !important;
    }
    .stFormSubmitButton > button { width: 100% !important; font-size: 1.2rem !important; margin-top: 1rem !important; }
    .stButton > button:hover, .stFormSubmitButton > button:hover {
        transform: translateY(-3px) !important; box-shadow: 0 8px 24px rgba(34,197,94,.6) !important;
    }

    .streamlit-expanderHeader {
        background-color: #334155 !important; border-radius: 8px !important; border: 1px solid #475569 !important;
        font-weight: 600 !important; color: #f1f5f9 !important;
    }
    .streamlit-expanderHeader:hover { background-color: #475569 !important; border-color: #22c55e !important; }
    .streamlit-expanderContent {
        background-color: #1e293b !important; border: 1px solid #475569 !important; border-top: none !important; color: #cbd5e1 !important;
    }

    .stAlert { background-color: #1e293b !important; border-radius: 8px !important; border-left: 4px solid #22c55e !important; color: #f1f5f9 !important; }
    .stSuccess { background-color: rgba(34,197,94,.1) !important; border-left-color: #22c55e !important; }
    .stWarning { background-color: rgba(251,191,36,.1) !important; border-left-color: #fbbf24 !important; }
    .stError { background-color: rgba(239,68,68,.1) !important; border-left-color: #ef4444 !important; }

    .stDownloadButton > button {
        background: transparent !important; color: #22c55e !important; border: 2px solid #22c55e !important;
        border-radius: 8px !important; padding: 0.75rem 1.5rem !important; font-weight: 600 !important; transition: all .3s ease !important;
    }
    .stDownloadButton > button:hover { background: #22c55e !important; color: white !important; transform: translateY(-2px) !important; box-shadow: 0 4px 12px rgba(34,197,94,.4) !important; }

    .stCheckbox { color: #f1f5f9 !important; }
    .stSpinner > div { border-top-color: #22c55e !important; }
    .stMarkdown, p { color: #cbd5e1; }
    h1,h2,h3,h4,h5,h6 { color: #f1f5f9 !important; }

    /* Custom Actions Table */
    .actions-table-container { overflow-x: auto; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,.3); }
    .actions-table { width: 100%; border-collapse: collapse; background: #1e293b; border-radius: 12px; overflow: hidden; }
    .actions-table thead { background: linear-gradient(135deg, #16a34a 0%, #22c55e 100%); }
    .actions-table th {
        padding: 1rem; text-align: left; color: white; font-weight: 600; font-size: .875rem; text-transform: uppercase; letter-spacing: .05em;
        border-bottom: 2px solid #22c55e;
    }
    .actions-table td { padding: 1rem; border-bottom: 1px solid #334155; color: #cbd5e1; font-size: .95rem; }
    .actions-table tbody tr { transition: all .2s ease; }
    .actions-table tbody tr:hover { background: #334155; transform: scale(1.01); }
    .action-name-cell { font-weight: 600; color: #22c55e; font-size: 1rem; }
    .action-value-cell { font-weight: 500; color: #f1f5f9; }
    .disruption-badge { display:inline-block; padding:.375rem .75rem; border-radius:16px; font-size:.75rem; font-weight:600; text-transform:uppercase; letter-spacing:.05em; }
    .badge-none,.badge-low { background: rgba(34,197,94,.2); color:#86efac; border: 1px solid rgba(34,197,94,.3); }
    .badge-medium { background: rgba(251,191,36,.2); color:#fbbf24; border: 1px solid rgba(251,191,36,.3); }
    .badge-high { background: rgba(239,68,68,.2); color:#f87171; border: 1px solid rgba(239,68,68,.3); }
</style>
""", unsafe_allow_html=True)

if "user" not in st.session_state:
    st.session_state.user = None
if "menu" not in st.session_state:
    st.session_state.menu = "Login"

st.markdown("""
            <div class="main-header" style="text-align:center;">
                <h1>⚡ Green Efficiency</h1>
                <p>Smart Energy Management for a Sustainable Future</p>
            </div>
        """, unsafe_allow_html=True)


menu = ["App"] if st.session_state.user else ["Login", "Sign Up"]
choice = st.selectbox("Menu", menu, index=menu.index(st.session_state.menu))

if choice == "Login":
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div class="energy-card"><div class="subsection-title">👋 Welcome Back!</div><p style="margin-bottom:1.5rem;">Login to track energy efficiency & save LKR!</p></div>', unsafe_allow_html=True)

        email = st.text_input("📧 Email Address", placeholder="your.email@example.com")
        password = st.text_input("Password", type="password", placeholder="Enter your password")

        if st.button("Login", use_container_width=True):
            user = login(email, password)
            if isinstance(user, dict):
                st.session_state.user = user
                st.success("Logged in successfully! Redirecting to app...")
                st.session_state.menu = "App"
                st.rerun()
            else:
                st.error(user)
        st.markdown('</div>', unsafe_allow_html=True)

elif choice == "Sign Up":
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div class="energy-card"><div class="subsection-title">✨ Create Your Account</div><p style="margin-bottom:1.5rem;">Sign up to start tracking energy efficiency!</p></div>', unsafe_allow_html=True)

        email = st.text_input("Email Address", placeholder="your.email@example.com")
        password = st.text_input("Password", type="password", placeholder="Create a strong password")

        if st.button("Sign Up", use_container_width=True):
            user = signup(email, password)
            if isinstance(user, dict):
                st.success("Account created! Please login.")
                st.session_state.menu = "Login"
                st.rerun()
            else:
                st.error(user)
        st.markdown('</div>', unsafe_allow_html=True)

elif choice == "App":
    if not st.session_state.user:
        st.warning("Please login first.")
        st.stop()

    lcol, rcol = st.columns([3, 1])
    with lcol:
        st.markdown(
            f'<div class="energy-card"><span style="color:#22c55e;font-weight:700;">LOGGED IN AS</span>'
            f'<div style="color:#f1f5f9;font-size:1.1rem;font-weight:700;margin-top:.25rem;">👤 {st.session_state.user["email"].split("@")[0]}</div>'
            f'</div>',
            unsafe_allow_html=True
        )
    with rcol:
        if st.button("🚪 Logout", use_container_width=True):
            logout()
            st.session_state.user = None
            st.session_state.menu = "Login"
            st.rerun()

    try:
        with open("data/defaults.yaml", "r", encoding="utf-8") as f:
            defaults = yaml.safe_load(f) or {}
    except Exception:
        defaults = {}
    tariff_default = float(defaults.get("tariff_LKR_per_kWh_default", 62))

    with st.expander("Derivation Context", expanded=False):
        derivation_tariff = st.number_input(
            "Tariff (currency per kWh)",
            min_value=0.0, value=0.20, step=0.01,
            help="Used to derive opex_change when missing",
            key="derivation_tariff"
        )
        derivation_grid = st.number_input(
            "Grid factor (kg CO₂e per kWh)",
            min_value=0.0, value=0.70, step=0.01,
            help="Used to derive CO2e_saved when missing",
            key="derivation_grid"
        )

    st.session_state["autofix_ctx"] = AutoFixContext(
        tariff_per_kwh=float(derivation_tariff),
        grid_kg_per_kwh=float(derivation_grid),
    )

    with st.form("input_form"):
        st.markdown('<div class="energy-card"><p class="section-title">🏢 Building & Devices</p></div>', unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            st.markdown('<p class="subsection-title">Building Information</p>', unsafe_allow_html=True)
            floor_area = st.number_input("Floor area (m²)", min_value=0.0, value=120.0, step=1.0)
            tariff = st.number_input("Tariff (LKR/kWh)", min_value=0.0, value=float(tariff_default), step=1.0)
        with col2:
            st.markdown('<p class="subsection-title">Monthly Consumption</p>', unsafe_allow_html=True)
            monthly_kwh = st.number_input("Monthly consumption (kWh)", min_value=0.0, value=320.0, step=1.0)

        st.markdown('<p class="subsection-title">Air Conditioning</p>', unsafe_allow_html=True)

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            ac_count = st.number_input("Number of AC units", min_value=0, value=1, step=1)
        with c2:
            ac_watt = st.number_input("Watt per unit", min_value=0, value=1200, step=50)
        with c3:
            ac_hours = st.number_input("Hours per day", min_value=0.0, max_value=24.0, value=8.0, step=0.5, key="ac_hours")
        with c4:
            ac_star = st.slider("Star rating", min_value=1, max_value=5, value=3)

        st.markdown('<p class="subsection-title">Lighting Configuration</p>', unsafe_allow_html=True)

        l1, l2, l3 = st.columns(3)
        with l1:
            bulbs = st.number_input("Number of bulbs", min_value=0, value=20, step=1)
        with l2:
            bulb_watt = st.number_input("Watt per bulb", min_value=0, value=10, step=1)
        with l3:
            bulb_hours = st.number_input("Hours per day", min_value=0.0, max_value=24.0, value=6.0, step=0.5, key="bulb_hours")

        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="energy-card"><p class="section-title">🎯 Goals & Policies</p></div>', unsafe_allow_html=True)

        st.markdown('<p class="subsection-title">Financial Goals</p>', unsafe_allow_html=True)
        f1, f2 = st.columns(2)
        with f1:
            target_budget = st.number_input(
                "Target budget (LKR)", min_value=0.0, step=1000.0, value=0.0,
                help="Total capex you're willing to spend across all actions.",
            )
        with f2:
            payback_thr = st.number_input(
                "Max payback (months)", min_value=0, step=1, value=0,
                help="Reject actions whose simple payback exceeds this.",
            )

        st.markdown('<p class="subsection-title">Environmental & Operational Goals</p>', unsafe_allow_html=True)
        g1, g2 = st.columns(2)
        with g1:
            co2_goal = st.slider(
                "CO₂ reduction goal (%)", min_value=0, max_value=100, value=0,
                help="Minimum monthly CO₂ reduction to aim for.",
            )
        with g2:
            max_disruption = st.selectbox(
                "Max acceptable disruption", options=["none", "low", "medium", "high"], index=2,
                help="Upper limit on disruption allowed for proposed actions.",
            )

        st.markdown('</div>', unsafe_allow_html=True)

        ctx = st.session_state.get("autofix_ctx")
        strict_mode = st.toggle(
            "Strict mode (no auto-fixes)",
            value=False,
            help="When ON, derived fields are NOT auto-filled. When OFF, we infer opex_change, CO₂e_saved, and payback_months where possible.",
        )


        submitted = st.form_submit_button("Run Comprehensive Analysis")

    if submitted:
        if bulb_hours < 0 or bulb_hours > 24:
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
                ] * int(ac_count),
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

            plan = result.get("plan", {}) or {}
            totals = plan.get("totals", {}) or {}

            st.markdown('<p class="section-title">Top 3 Quick Wins</p>', unsafe_allow_html=True)
            quick = plan.get("quick_wins", []) or []
            cols = st.columns(3) if len(quick) >= 3 else st.columns(len(quick) or 1)
            for i, item in enumerate(quick[:3]):
                with cols[i % len(cols)]:
                    st.markdown(
                        f'''
                        <div class="metric-card">
                            <div class="metric-label">
                                {item.get("action", f"Action {i+1}")}
                            </div>
                            <div class="metric-value">
                                {item.get("LKR_saved_per_month", 0):.0f} LKR/mo
                            </div>
                            <div class="metric-sublabel">
                                {item.get("kWh_saved_per_month", 0):.0f} kWh/mo saved
                            </div>
                        </div>
                        ''',
                        unsafe_allow_html=True
                    )
            

            st.markdown('</n><p class="section-title">All Actions</p>', unsafe_allow_html=True)
            df = pd.DataFrame(plan.get("all_actions", []) or [])
            if not df.empty:
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

                def badge(disruption: str) -> str:
                    d = (disruption or "").lower()
                    cls = "badge-medium"
                    if d in ("none","low"): cls = "badge-low"
                    elif d == "high": cls = "badge-high"
                    return f'<span class="disruption-badge {cls}">{disruption or "-"}</span>'

                table_html = ['<div class="actions-table-container"><table class="actions-table">']
                table_html.append("<thead><tr>")
                for col in df.columns:
                    table_html.append(f"<th>{col.replace('_',' ').title()}</th>")
                table_html.append("</tr></thead><tbody>")
                for _, row in df.iterrows():
                    table_html.append("<tr>")
                    for col in df.columns:
                        val = row.get(col, "")
                        if col == "action":
                            cell = f'<td class="action-name-cell">{val}</td>'
                        elif col == "disruption":
                            cell = f"<td>{badge(val)}</td>"
                        else:
                            cell = f'<td class="action-value-cell">{val if val != "" else "-"}</td>'
                        table_html.append(cell)
                    table_html.append("</tr>")
                table_html.append("</tbody></table></div>")
                st.markdown("".join(table_html), unsafe_allow_html=True)
            else:
                st.info("No actions returned.")

            findings = result.get("findings", {})
            if findings and "findings" in findings:
                st.markdown('<p class="section-title">Audit Findings (Energy Inefficiencies)</p>', unsafe_allow_html=True)
                findings_list = findings["findings"]
                if findings_list:
                    st.markdown('<div class="energy-card">', unsafe_allow_html=True)
                    findings_df = pd.DataFrame(findings_list)
                    st.dataframe(findings_df, use_container_width=True)
                    with st.expander("Show raw findings JSON"):
                        st.json(findings)
                    st.markdown('</div>', unsafe_allow_html=True)
                # else:
                #     st.info("No inefficiencies found by the auditor.")
            total_kwh = float(totals.get("kWh_saved_per_month", 0.0) or 0.0)
            total_lkr = float(totals.get("LKR_saved_per_month", 0.0) or 0.0)
            total_co2 = float(totals.get("co2_kg_saved_per_month", 0.0) or 0.0)
            st.markdown(
                f'<div class="energy-card" style="text-align:center;"><div class="metric-label">Estimated Total Impact</div>'
                f'<div class="metric-value" style="font-size:2rem;">{total_kwh:.0f} kWh/mo • {total_lkr:.0f} LKR/mo • {total_co2:.1f} kgCO₂/mo</div></div>',
                unsafe_allow_html=True
            )

            st.markdown('<p class="section-title">Policy Enforcement</p>', unsafe_allow_html=True)
            effective_policy = plan.get("policy") or payload.get("policy") or {}
            b1, b2, b3, b4 = st.columns(4)
            def fmt_budget(v):
                return "∞" if v in (None, 0) else f"{int(v):,} LKR"
            def fmt_payback(v):
                return "∞" if v in (None, 0) else f"{int(v)} mo"
            def fmt_co2(v):
                return "—" if v in (None, 0) else f"{int(v)}%"

            b1.markdown(
                f'<div class="metric-card">'
                f'<div class="metric-label">Budget</div>'
                f'<div class="metric-value">{fmt_budget(effective_policy.get("target_budget_LKR"))}</div>'
                f'</div>',
                unsafe_allow_html=True
            )

            b2.markdown(
                f'<div class="metric-card">'
                f'<div class="metric-label">Max Payback</div>'
                f'<div class="metric-value">{fmt_payback(effective_policy.get("payback_threshold_months"))}</div>'
                f'</div>',
                unsafe_allow_html=True
            )

            b3.markdown(
                f'<div class="metric-card">'
                f'<div class="metric-label">CO₂ Goal</div>'
                f'<div class="metric-value">{fmt_co2(effective_policy.get("co2_reduction_goal_pct"))}</div>'
                f'</div>',
                unsafe_allow_html=True
            )

            b4.markdown(
                f'<div class="metric-card">'
                f'<div class="metric-label">Max Disruption</div>'
                f'<div class="metric-value">{effective_policy.get("max_disruption","medium").title()}</div>'
                f'</div>',
                unsafe_allow_html=True
            )

            recs = result.get("recommendations", {}) or {}
            policy_report = recs.get("policy_report") or {}
            notes = policy_report.get("notes") or []
            if notes:
                with st.expander("What was enforced?"):
                    for n in notes:
                        st.write("- " + str(n))

            raw = plan.get("plan_text", "")
            clean = re.sub(r'^\s*#{1,6}\s*', '', raw, count=1)
            lines = clean.splitlines()
            html_lines, in_list = [], False   
            def md_inline(s: str) -> str:
                s = html.escape(s)
                s = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s)
                return s

            for line in lines:
                if line.strip().startswith('- '):
                    if not in_list:
                        html_lines.append('<ul>')
                        in_list = True
                    html_lines.append(f'<li>{md_inline(line.strip()[2:])}</li>')
                else:
                    if in_list:
                        html_lines.append('</ul>')
                        in_list = False
                    if line.strip():
                        html_lines.append(f'<p>{md_inline(line)}</p>')

            if in_list:
                html_lines.append('</ul>')

            body_html = ''.join(html_lines)

            st.markdown('</n><p class="section-title">Action Plan</p>', unsafe_allow_html=True)

            st.markdown(
                f"""
                <div class="energy-card">
                <div class="plan-text">
                    {body_html}
                </div>
                <a
                    class="download-btn"
                    href="data:text/markdown;charset=utf-8,{ul.quote(clean)}"
                    download="action_plan.md"
                >
                    Download Action Plan (.md)
                </a>
                </div>
                """,
                unsafe_allow_html=True
            )
            
            raw_actions = plan.get("actions", []) or []
            if not raw_actions:
                legacy = plan.get("all_actions", []) or []
                raw_actions = []
                for a in legacy:
                    try:
                        kwh_pm = float(a.get("kWh_saved_per_month", 0.0) or 0.0)
                        lkr_pm = a.get("LKR_saved_per_month", None)
                        raw_actions.append(
                            {
                                "action": a.get("action", "") or "Unnamed action",
                                "capex": float(a.get("est_cost", 0.0) or 0.0),
                                "annual_kWh_saved": kwh_pm * 12.0,
                                "opex_change": -(float(lkr_pm) * 12.0) if lkr_pm not in (None, "") else None,
                                "CO2e_saved": float(a.get("co2_kg_saved_per_month", 0.0) or 0.0) * 12.0,
                                "payback_months": float(a.get("payback_months", 0.0) or 0.0) or None,
                                "confidence": float(a.get("confidence", 0.7)),
                            }
                        )
                    except Exception:
                        continue

            report = validate_actions_report(raw_actions, ctx=ctx, strict=strict_mode)

            if report.issues:
                st.warning("Some rows failed validation. Valid rows are shown below; expand to see issues per row.")
                with st.expander("Show validation issues"):
                    for iss in report.issues:
                        st.write(f"- Row {iss.row_index + 1} · **{iss.field}**: {iss.message}")

            structured = report.objects
            notes = report.notes_per_row
            st.session_state["structured_actions"] = structured
            st.session_state["structured_notes"] = notes

            # st.markdown('<p class="section-title">Structured actions (validated)</p>', unsafe_allow_html=True)
            # if structured:
            #     s_df = pd.DataFrame([s.model_dump() for s in structured])
            #     st.markdown('<div class="energy-card">', unsafe_allow_html=True)
            #     st.dataframe(s_df, use_container_width=True)
            #     st.markdown('</div>', unsafe_allow_html=True)
            # else:
            #     st.info("No valid structured actions to display.")

            # with st.expander("Auto-fix notes per row"):
            #     for i, ns in enumerate(notes):
            #         if ns:
            #             st.markdown(f"**Row {i+1}:**")
            #             for n in ns:
            #                 st.write("- " + str(n))
            #         else:
            #             st.write(f"**Row {i+1}:** (no fixes)")
