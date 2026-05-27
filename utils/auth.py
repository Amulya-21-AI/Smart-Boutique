"""utils/auth.py — shared auth helpers for Smart Boutique"""
import streamlit as st

GOLD = "#c9a96e"

GLOBAL_CSS = """<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=DM+Sans:wght@300;400;500&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
h1, h2, h3 { font-family: 'Playfair Display', serif !important; }
section[data-testid="stSidebar"] {
    background: linear-gradient(160deg, #1a0a2e 0%, #16213e 60%, #0f3460 100%);
}
section[data-testid="stSidebar"] * { color: #f5e6d3 !important; }
[data-testid="metric-container"] {
    background: linear-gradient(135deg, #1a0a2e22, #0f346022);
    border: 1px solid #c9a96e44; border-radius: 12px; padding: 1rem;
}
.stButton > button {
    background: linear-gradient(135deg, #c9a96e, #e8c99a);
    color: #1a0a2e; font-weight: 600; border: none;
    border-radius: 8px; padding: 0.5rem 1.5rem;
}
.stButton > button:hover {
    background: linear-gradient(135deg, #e8c99a, #c9a96e);
    transform: translateY(-1px);
}
[data-testid="stSidebarNav"] { display: none !important; }
</style>"""


def _show_sidebar_nav():
    role     = st.session_state.get('role', '')
    username = st.session_state.get('username', '')
    cust_id  = st.session_state.get('cust_id')

    with st.sidebar:
        icon  = "👑" if role == 'admin' else "👤"
        label = "Administrator" if role == 'admin' else f"Customer #{cust_id}"
        st.markdown(f"""
<div style='padding:0.8rem;background:#ffffff11;border-radius:10px;
            border:1px solid #c9a96e44;margin-bottom:1rem;'>
  <div style='font-size:1.05rem;font-weight:600;color:#c9a96e;'>{icon} {username}</div>
  <div style='font-size:0.75rem;color:#aaa88;text-transform:uppercase;
              letter-spacing:1px;margin-top:2px;'>{label}</div>
</div>""", unsafe_allow_html=True)

        if role == 'admin':
            st.page_link("Main.py",                         label="🏠 Home")
            st.page_link("pages/Dashboard.py",              label="📊 Analytics Dashboard")
            st.page_link("pages/Customers.py",              label="👥 Customers")
            st.page_link("pages/Orders.py",                 label="📦 Orders")
            st.page_link("pages/Tailors.py",                label="✂️ Tailors")
            st.markdown("---")
            st.caption("AI & ML Tools")
            st.page_link("pages/GenAI_RAG_Assistant.py",    label="✨ AI Fashion Assistant")
            st.page_link("pages/ML_Recommendation.py",      label="🎯 Recommendations")
            st.page_link("pages/ML_DeliveryPrediction.py",  label="🚚 Delivery Prediction")
            st.page_link("pages/ML_DemandForecast.py",      label="📈 Demand Forecast")
            st.page_link("pages/ML_ReturnPrediction.py",    label="🔄 Return Prediction")
            st.page_link("pages/AI_Assistant.py",           label="🤖 ML Readiness Hub")
        else:
            st.page_link("Main.py",                         label="🏠 My Dashboard")
            st.page_link("pages/My_Profile.py",             label="👤 My Profile & Orders")
            st.page_link("pages/Orders.py",                 label="📦 Place / Track Order")
            st.page_link("pages/GenAI_RAG_Assistant.py",   label="✨ AI Style Advisor")
            st.page_link("pages/ML_Recommendation.py",     label="🎯 Style Recommendations")
            st.page_link("pages/ML_DeliveryPrediction.py", label="🚚 Delivery Tracker")

        st.markdown("---")
        if st.button("🚪 Logout", use_container_width=True, key="_logout_btn"):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.switch_page("pages/Login.py")


def require_auth(allowed_roles=None):
    """
    Call right after st.set_page_config() in every page.
    Applies CSS, enforces auth + role, renders sidebar nav.
    Returns (role, cust_id).
    """
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

    if not st.session_state.get('authenticated'):
        st.warning("Please log in to access this page.")
        if st.button("Go to Login →", key="_to_login"):
            st.switch_page("pages/Login.py")
        st.stop()

    role    = st.session_state.get('role', '')
    cust_id = st.session_state.get('cust_id')

    if allowed_roles and role not in allowed_roles:
        st.error("Access denied. You don't have permission to view this page.")
        if st.button("← Back to Home", key="_back_home"):
            st.switch_page("Main.py")
        st.stop()

    _show_sidebar_nav()
    return role, cust_id
