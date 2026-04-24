"""
Smart-Boutique/main.py
-----------------------
Run: streamlit run main.py
"""

import streamlit as st
import os
import sys
from PIL import Image

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from database.db import init_db, load_csv_to_orders, run_query

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Anjali Ladies Boutique",
    page_icon="🧵",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=DM+Sans:wght@300;400;500&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
h1, h2, h3 { font-family: 'Playfair Display', serif !important; }
section[data-testid="stSidebar"] {
    background: linear-gradient(160deg, #1a0a2e 0%, #16213e 60%, #0f3460 100%);
}
section[data-testid="stSidebar"] * { color: #f5e6d3 !important; }
[data-testid="metric-container"] {
    background: linear-gradient(135deg, #1a0a2e22, #0f346022);
    border: 1px solid #c9a96e44;
    border-radius: 12px;
    padding: 1rem;
}
.stButton > button {
    background: linear-gradient(135deg, #c9a96e, #e8c99a);
    color: #1a0a2e; font-weight: 600;
    border: none; border-radius: 8px; padding: 0.5rem 1.5rem;
}
.stButton > button:hover {
    background: linear-gradient(135deg, #e8c99a, #c9a96e);
    transform: translateY(-1px);
}
</style>
""", unsafe_allow_html=True)

# ── One-time DB init ──────────────────────────────────────────────────────────
init_db()

# ── Seed CSV once ─────────────────────────────────────────────────────────────
CSV_PATH  = os.path.join(ROOT, "data", "women_cleaned.csv")
# Fallback to original if women-only file not generated yet
if not os.path.exists(CSV_PATH):
    CSV_PATH = os.path.join(ROOT, "data", "cleaned_data.csv")
SEED_FLAG = os.path.join(ROOT, "database", ".seeded")

if not os.path.exists(SEED_FLAG) and os.path.exists(CSV_PATH):
    with st.spinner("🌱 Loading order history into database — one time only…"):
        inserted, skipped = load_csv_to_orders(CSV_PATH)
    open(SEED_FLAG, "w").close()
    st.success(f"✅ Loaded {inserted:,} orders into the database successfully!")

# ── LOGO + HEADER ─────────────────────────────────────────────────────────────
logo_path = os.path.join(ROOT, "project.jpeg")

col_logo, col_title = st.columns([1, 4])
with col_logo:
    if os.path.exists(logo_path):
        logo = Image.open(logo_path)
        st.image(logo, width=180)

with col_title:
    st.markdown("""
    <div style="padding-top: 1rem;">
        <h1 style="color:#c9a96e; margin-bottom:0;">Anjali Ladies Boutique</h1>
        <p style="color:#aaa; font-size:1.1rem; margin-top:0.3rem;">
            Muggam &nbsp;·&nbsp; Embroidery &nbsp;·&nbsp; Customization Available
        </p>
        <p style="color:#888; font-size:0.95rem;">
        </p>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# ── Quick Stats ───────────────────────────────────────────────────────────────
try:
    kpi = run_query("""
        SELECT COUNT(DISTINCT order_id) AS orders,
               SUM(amount)              AS revenue,
               COUNT(DISTINCT cust_id)  AS customers,
               ROUND(AVG(amount), 0)    AS avg_order
        FROM orders WHERE status NOT IN ('Cancelled')
    """)
    if len(kpi):
        k = kpi.iloc[0]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("📦 Total Orders",     f"{int(k['orders']   or 0):,}")
        c2.metric("💰 Total Revenue",    f"₹{int(k['revenue'] or 0):,}")
        c3.metric("👥 Unique Customers", f"{int(k['customers'] or 0):,}")
        c4.metric("💳 Avg Order Value",  f"₹{int(k['avg_order'] or 0):,}")
except Exception:
    pass

st.markdown("<br>", unsafe_allow_html=True)

# ── Page Cards ────────────────────────────────────────────────────────────────
col1, col2, col3 = st.columns(3)
with col1:
    st.info("**📊 Dashboard**\nSales analytics, KPIs, trends and supplier performance.")
with col2:
    st.info("**👥 Customers**\nRegister new customers and view existing records.")
with col3:
    st.info("**📦 Orders**\nBrowse, filter and manage all orders.")

col4, col5, col6 = st.columns(3)
with col4:
    st.info("**✂️ Tailors**\nManage tailor profiles and availability.")
with col5:
    st.warning("**🤖 ML Recommendations** \nDelivery prediction & design recommendations.")
with col6:
    st.warning("**✨ AI Fashion Assistant** \nGenAI-powered style advice.")

st.markdown("<br><hr>", unsafe_allow_html=True)
st.caption("Anjali Ladies Boutique · Smart Management System . Contact Us: 9876543210 ")
 