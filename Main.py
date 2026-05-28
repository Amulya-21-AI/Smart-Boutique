"""
Smart-Boutique/Main.py
Run: streamlit run Main.py
"""
import os, sys
ROOT = os.path.dirname(os.path.abspath(__file__))
# Ensure project root is always on the Python path (local + Railway)
for _p in [ROOT, "/app"]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

import streamlit as st
from PIL import Image
from database.db import init_db, load_csv_to_orders, run_query, ensure_default_admin

st.set_page_config(
    page_title="AMK Fashion Hub",
    page_icon="🧵",
    layout="wide",
    initial_sidebar_state="expanded"
)

init_db()
ensure_default_admin()

# ── Seed CSV once ─────────────────────────────────────────────────────────────
CSV_PATH  = os.path.join(ROOT, "data", "women_cleaned.csv")
if not os.path.exists(CSV_PATH):
    CSV_PATH = os.path.join(ROOT, "data", "cleaned_data.csv")
SEED_FLAG = os.path.join(ROOT, "database", ".seeded")

if not os.path.exists(SEED_FLAG) and os.path.exists(CSV_PATH):
    with st.spinner("Loading order history — one time only…"):
        inserted, skipped = load_csv_to_orders(CSV_PATH)
    open(SEED_FLAG, "w").close()

# ── Auth check ────────────────────────────────────────────────────────────────
from utils.auth import require_auth, GOLD, GLOBAL_CSS

if not st.session_state.get('authenticated'):
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)
    logo_path = os.path.join(ROOT, "project.jpeg")
    col_logo, col_title = st.columns([1, 4])
    with col_logo:
        if os.path.exists(logo_path):
            st.image(Image.open(logo_path), width=160)
    with col_title:
        st.markdown(f"""
<div style='padding-top:0.8rem;'>
  <h1 style='color:{GOLD};margin-bottom:0;'>AMK Fashion Hub</h1>
  <p style='color:#aaa;margin-top:0.2rem;'>Anjali Ladies Boutique · Muggam, Kerala</p>
</div>""", unsafe_allow_html=True)

    st.divider()
    st.markdown("#### Welcome — please log in or register to continue.")
    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        if st.button("🔐 Login", use_container_width=True):
            st.switch_page("pages/Login.py")
    with c2:
        if st.button("📝 Register", use_container_width=True):
            st.switch_page("pages/Login.py")
    st.stop()

role, cust_id = require_auth()   # sets up sidebar nav

logo_path = os.path.join(ROOT, "project.jpeg")

# ══════════════════════════════════════════════════════════════════════════════
# ADMIN HOME
# ══════════════════════════════════════════════════════════════════════════════
if role == 'admin':
    col_logo, col_title = st.columns([1, 4])
    with col_logo:
        if os.path.exists(logo_path):
            st.image(Image.open(logo_path), width=160)
    with col_title:
        st.markdown(f"""
<div style='padding-top:0.8rem;'>
  <h1 style='color:{GOLD};margin-bottom:0;'>AMK Fashion Hub — Admin</h1>
  <p style='color:#aaa;margin-top:0.2rem;'>Anjali Ladies Boutique · Muggam, Kerala</p>
</div>""", unsafe_allow_html=True)

    st.divider()

    # ── Revenue KPIs ──────────────────────────────────────────────────────────
    try:
        kpi = run_query("""
            SELECT
                COUNT(DISTINCT order_id)                                    AS total_orders,
                SUM(CASE WHEN status NOT IN ('Cancelled','Returned')
                         THEN amount ELSE 0 END)                            AS confirmed_revenue,
                COUNT(DISTINCT CASE WHEN status NOT IN ('Cancelled','Returned')
                                    THEN order_id END)                      AS confirmed_orders,
                COUNT(DISTINCT cust_id)                                     AS unique_customers,
                ROUND(AVG(CASE WHEN status NOT IN ('Cancelled','Returned')
                               THEN amount END), 0)                         AS avg_order
            FROM orders
        """)
        k = kpi.iloc[0]
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("📦 Total Orders",        f"{int(k['total_orders']   or 0):,}")
        c2.metric("✅ Confirmed Orders",     f"{int(k['confirmed_orders'] or 0):,}")
        c3.metric("💰 Confirmed Revenue",   f"₹{int(k['confirmed_revenue'] or 0):,}")
        c4.metric("👥 Unique Customers",    f"{int(k['unique_customers'] or 0):,}")
        c5.metric("💳 Avg Order Value",     f"₹{int(k['avg_order'] or 0):,}")
    except Exception:
        pass

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Monthly customer growth ───────────────────────────────────────────────
    try:
        import plotly.express as px

        monthly = run_query("""
            SELECT strftime('%Y-%m', created_at) AS month,
                   COUNT(DISTINCT cust_id)       AS new_customers
            FROM customers
            WHERE created_at IS NOT NULL
            GROUP BY month
            ORDER BY month DESC
            LIMIT 12
        """)
        monthly = monthly.sort_values('month')

        order_monthly = run_query("""
            SELECT strftime('%Y-%m', order_date) AS month,
                   SUM(CASE WHEN status NOT IN ('Cancelled','Returned')
                            THEN amount ELSE 0 END) AS revenue,
                   COUNT(DISTINCT order_id)          AS orders
            FROM orders
            WHERE order_date IS NOT NULL
            GROUP BY month
            ORDER BY month DESC
            LIMIT 12
        """)
        order_monthly = order_monthly.sort_values('month')

        col_a, col_b = st.columns(2)

        with col_a:
            st.markdown(f"<h3 style='color:{GOLD}'>📈 Monthly New Customers</h3>",
                        unsafe_allow_html=True)
            if not monthly.empty:
                fig = px.bar(monthly, x='month', y='new_customers',
                             color_discrete_sequence=['#c9a96e'],
                             labels={'month': 'Month', 'new_customers': 'New Customers'})
                fig.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                    font_color='#f5e6d3', margin=dict(l=0,r=0,t=20,b=0)
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No customer data yet.")

        with col_b:
            st.markdown(f"<h3 style='color:{GOLD}'>💰 Monthly Revenue</h3>",
                        unsafe_allow_html=True)
            if not order_monthly.empty:
                fig2 = px.line(order_monthly, x='month', y='revenue',
                               markers=True,
                               color_discrete_sequence=['#c9a96e'],
                               labels={'month': 'Month', 'revenue': 'Revenue (₹)'})
                fig2.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                    font_color='#f5e6d3', margin=dict(l=0,r=0,t=20,b=0)
                )
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("No order data yet.")

    except Exception:
        pass

    st.divider()

    # ── Quick nav cards ───────────────────────────────────────────────────────
    st.markdown(f"<h3 style='color:{GOLD}'>Quick Access</h3>", unsafe_allow_html=True)
    r1c1, r1c2, r1c3, r1c4 = st.columns(4)
    r1c1.info("**📊 Analytics Dashboard**\nDetailed sales, category & supplier insights.")
    r1c2.info("**👥 Customers**\nRegister and manage customer records.")
    r1c3.info("**📦 Orders**\nView, filter and manage all orders.")
    r1c4.info("**✂️ Tailors**\nRegister tailors and assign work.")

    r2c1, r2c2, r2c3, r2c4 = st.columns(4)
    r2c1.warning("**✨ AI Assistant**\nGenAI-powered fashion advice.")
    r2c2.warning("**🎯 Recommendations**\nML-based design suggestions.")
    r2c3.warning("**🚚 Delivery Prediction**\nForecast delivery timelines.")
    r2c4.warning("**📈 Demand Forecast**\nSeasonal demand planning.")

# ══════════════════════════════════════════════════════════════════════════════
# CUSTOMER HOME
# ══════════════════════════════════════════════════════════════════════════════
else:
    username = st.session_state.get('username', '')
    col_logo, col_title = st.columns([1, 4])
    with col_logo:
        if os.path.exists(logo_path):
            st.image(Image.open(logo_path), width=160)
    with col_title:
        st.markdown(f"""
<div style='padding-top:0.8rem;'>
  <h1 style='color:{GOLD};margin-bottom:0;'>Welcome, {username}!</h1>
  <p style='color:#aaa;margin-top:0.2rem;'>
    Anjali Ladies Boutique · Your personal fashion portal
  </p>
  <p style='color:#888;font-size:0.9rem;'>
    Customer ID: <strong style='color:{GOLD};'>CUST-{cust_id}</strong>
  </p>
</div>""", unsafe_allow_html=True)

    st.divider()

    # ── Customer KPIs ─────────────────────────────────────────────────────────
    try:
        ckpi = run_query("""
            SELECT COUNT(order_id)                                         AS total_orders,
                   SUM(CASE WHEN status NOT IN ('Cancelled','Returned')
                            THEN amount ELSE 0 END)                        AS total_spent,
                   COUNT(CASE WHEN status IN ('Pending','Shipped')
                              THEN 1 END)                                  AS active_orders,
                   COUNT(CASE WHEN status='Delivered' THEN 1 END)          AS completed
            FROM orders WHERE cust_id=?
        """, (cust_id,))
        ck = ckpi.iloc[0]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("📦 My Orders",      f"{int(ck['total_orders']  or 0):,}")
        c2.metric("💰 Total Spent",    f"₹{int(ck['total_spent']  or 0):,}")
        c3.metric("⏳ Active",         f"{int(ck['active_orders'] or 0):,}")
        c4.metric("✅ Completed",      f"{int(ck['completed']     or 0):,}")
    except Exception:
        pass

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f"<h3 style='color:{GOLD}'>What would you like to do?</h3>",
                unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.info("**👤 My Profile & Orders**\nView your order history, track progress and see your tailor.")
        if st.button("View My Profile", use_container_width=True):
            st.switch_page("pages/My_Profile.py")
    with c2:
        st.info("**📦 Place / Track Order**\nPlace a new custom order or track an existing one.")
        if st.button("Go to Orders", use_container_width=True):
            st.switch_page("pages/Orders.py")
    with c3:
        st.info("**✨ AI Style Advisor**\nGet personalised fashion advice from our AI assistant.")
        if st.button("Open AI Advisor", use_container_width=True):
            st.switch_page("pages/GenAI_RAG_Assistant.py")

    c4, c5, c6 = st.columns(3)
    with c4:
        st.warning("**🎯 Style Recommendations**\nAI picks based on your preferences.")
        if st.button("Get Recommendations", use_container_width=True):
            st.switch_page("pages/ML_Recommendation.py")
    with c5:
        st.warning("**🚚 Delivery Tracker**\nPredict when your order will arrive.")
        if st.button("Track Delivery", use_container_width=True):
            st.switch_page("pages/ML_DeliveryPrediction.py")
    with c6:
        st.info("**☎️ Contact Boutique**\nReach us at **9876543210**  \nMuggam, Kerala.")

st.markdown("<br><hr>", unsafe_allow_html=True)
st.caption("AMK Fashion Hub · Anjali Ladies Boutique · Muggam, Kerala")
