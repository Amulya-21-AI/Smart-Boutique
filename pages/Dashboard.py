"""
Smart-Boutique/pages/Dashboard.py
"""
import os, sys

# pages/ is directly inside Smart-Boutique/
# So ROOT = one level up from this file
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import streamlit as st
import plotly.express as px
from database.db import init_db, run_query

st.set_page_config(page_title="Dashboard · Smart Boutique", page_icon="📊", layout="wide")
init_db()

GOLD    = "#c9a96e"
PALETTE = ["#c9a96e","#e8c99a","#8b5e3c","#1a0a2e","#0f3460",
           "#16213e","#e74c3c","#2ecc71","#3498db","#9b59b6"]

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=DM+Sans:wght@300;400;500&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
h1,h2,h3 { font-family: 'Playfair Display', serif !important; }
section[data-testid="stSidebar"] {
    background: linear-gradient(160deg, #1a0a2e 0%, #16213e 60%, #0f3460 100%);
}
section[data-testid="stSidebar"] * { color: #f5e6d3 !important; }
[data-testid="metric-container"] {
    background: linear-gradient(135deg, #1a0a2e22, #0f346022);
    border: 1px solid #c9a96e44; border-radius: 12px; padding: 1rem;
}
</style>
""", unsafe_allow_html=True)

st.markdown(f"<h1 style='color:{GOLD}'>📊 Analytics Dashboard</h1>", unsafe_allow_html=True)

# ── Sidebar Filters ───────────────────────────────────────────────────────────
st.sidebar.header("🔎 Filters")

categories = run_query("SELECT DISTINCT category FROM orders WHERE category IS NOT NULL ORDER BY category")["category"].tolist()
suppliers  = run_query("SELECT DISTINCT retail_supplier FROM orders WHERE retail_supplier IS NOT NULL ORDER BY retail_supplier")["retail_supplier"].tolist()

sel_cat = st.sidebar.multiselect("Category", categories, default=categories)
sel_sup = st.sidebar.multiselect("Supplier",  suppliers,  default=suppliers)
sel_sea = st.sidebar.multiselect("Season",    ["Spring","Summer","Autumn","Winter"],
                                              default=["Spring","Summer","Autumn","Winter"])
sel_b2b = st.sidebar.radio("Order Type", ["All","B2B Only","B2C Only"], index=0)

b2b_clause = {"B2B Only":"AND b2b=1","B2C Only":"AND b2b=0"}.get(sel_b2b,"")
# FIX: if filter is empty, fall back to full list so dashboard never goes blank
_cats = sel_cat if sel_cat else categories
_sups = sel_sup if sel_sup else suppliers
_seas = sel_sea if sel_sea else ["Spring","Summer","Autumn","Winter"]
cat_in = ",".join([f"'{c}'" for c in _cats])
sup_in = ",".join([f"'{s}'" for s in _sups])
sea_in = ",".join([f"'{s}'" for s in _seas])

BASE = f"""FROM orders
           WHERE status NOT IN ('Cancelled')
           AND category IN ({cat_in})
           AND (retail_supplier IN ({sup_in}) OR retail_supplier IS NULL)
           AND (season IN ({sea_in}) OR season IS NULL)
           {b2b_clause}"""

# ── KPIs ──────────────────────────────────────────────────────────────────────
kpi = run_query(f"""
    SELECT COUNT(DISTINCT order_id) AS total_orders,
           SUM(amount)              AS total_revenue,
           AVG(amount)              AS avg_order,
           SUM(qty)                 AS total_units,
           SUM(return_flag)         AS returns,
           COUNT(DISTINCT cust_id)  AS unique_custs
    {BASE}
""")
if len(kpi):
    k = kpi.iloc[0]
    c1,c2,c3,c4,c5,c6 = st.columns(6)
    total_ord = int(k['total_orders'] or 0)
    returns   = int(k['returns']      or 0)
    ret_rate  = round(returns / total_ord * 100, 1) if total_ord > 0 else 0
    c1.metric("📦 Orders",        f"{total_ord:,}")
    c2.metric("💰 Revenue (₹)",   f"{int(k['total_revenue'] or 0):,}")
    c3.metric("📈 Avg Order (₹)", f"{float(k['avg_order']   or 0):.0f}")
    c4.metric("🛍️ Units Sold",    f"{int(k['total_units']   or 0):,}")
    c5.metric("🔄 Returns",       f"{returns:,}", f"{ret_rate}% return rate")
    c6.metric("👥 Customers",     f"{int(k['unique_custs']  or 0):,}")

st.divider()

# ── Row 1: Category Bar + Monthly Trend ──────────────────────────────────────
col1, col2 = st.columns(2)
with col1:
    st.subheader("Sales by Category")
    df_cat = run_query(f"SELECT category, SUM(amount) AS revenue {BASE} GROUP BY category ORDER BY revenue DESC")
    if len(df_cat):
        fig = px.bar(df_cat, x="category", y="revenue", color="category",
                     color_discrete_sequence=PALETTE)
        fig.update_layout(showlegend=False, plot_bgcolor="rgba(0,0,0,0)",
                          paper_bgcolor="rgba(0,0,0,0)", font_color="#aaa")
        st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("Monthly Revenue Trend")
    df_mon = run_query(f"""
        SELECT strftime('%Y-%m', order_date) AS month, SUM(amount) AS revenue
        {BASE} AND order_date IS NOT NULL
        GROUP BY month ORDER BY month
    """)
    if len(df_mon):
        fig2 = px.area(df_mon, x="month", y="revenue", color_discrete_sequence=[GOLD])
        fig2.update_layout(plot_bgcolor="rgba(0,0,0,0)",
                           paper_bgcolor="rgba(0,0,0,0)", font_color="#aaa")
        st.plotly_chart(fig2, use_container_width=True)

# ── Row 2: Gender Donut + Size Bar ───────────────────────────────────────────
col3, col4 = st.columns(2)
with col3:
    st.subheader("Orders by Gender")
    df_gen = run_query(f"SELECT gender, COUNT(*) AS cnt {BASE} AND gender IS NOT NULL GROUP BY gender")
    if len(df_gen):
        fig3 = px.pie(df_gen, values="cnt", names="gender",
                      color_discrete_sequence=PALETTE, hole=0.45)
        fig3.update_layout(plot_bgcolor="rgba(0,0,0,0)",
                           paper_bgcolor="rgba(0,0,0,0)", font_color="#aaa")
        st.plotly_chart(fig3, use_container_width=True)

with col4:
    st.subheader("Size Distribution")
    df_size = run_query(f"SELECT size, SUM(qty) AS qty {BASE} AND size IS NOT NULL GROUP BY size ORDER BY qty DESC")
    if len(df_size):
        fig4 = px.bar(df_size, x="size", y="qty", color="size",
                      color_discrete_sequence=PALETTE)
        fig4.update_layout(showlegend=False, plot_bgcolor="rgba(0,0,0,0)",
                           paper_bgcolor="rgba(0,0,0,0)", font_color="#aaa")
        st.plotly_chart(fig4, use_container_width=True)

# ── Row 3: Season Heatmap + Top States ───────────────────────────────────────
col5, col6 = st.columns(2)
with col5:
    st.subheader("Revenue by Season & Category")
    df_sc = run_query(f"""
        SELECT season, category, SUM(amount) AS revenue
        {BASE} AND season IS NOT NULL
        GROUP BY season, category
    """)
    if len(df_sc):
        pivot = df_sc.pivot(index="season", columns="category", values="revenue").fillna(0)
        fig5  = px.imshow(pivot, color_continuous_scale="YlOrBr")
        fig5.update_layout(plot_bgcolor="rgba(0,0,0,0)",
                           paper_bgcolor="rgba(0,0,0,0)", font_color="#aaa")
        st.plotly_chart(fig5, use_container_width=True)

with col6:
    st.subheader("Top 10 States by Revenue")
    df_state = run_query(f"""
        SELECT ship_state AS state, SUM(amount) AS revenue
        {BASE} AND ship_state IS NOT NULL
        GROUP BY ship_state ORDER BY revenue DESC LIMIT 10
    """)
    if len(df_state):
        fig6 = px.bar(df_state, x="revenue", y="state", orientation="h",
                      color="revenue", color_continuous_scale="YlOrBr")
        fig6.update_layout(yaxis=dict(autorange="reversed"),
                           plot_bgcolor="rgba(0,0,0,0)",
                           paper_bgcolor="rgba(0,0,0,0)", font_color="#aaa")
        st.plotly_chart(fig6, use_container_width=True)

# ── Supplier Table ────────────────────────────────────────────────────────────
st.subheader("🏭 Retail Supplier Performance")
df_sup = run_query(f"""
    SELECT retail_supplier AS supplier,
           COUNT(DISTINCT order_id)                  AS orders,
           SUM(amount)                               AS revenue,
           ROUND(AVG(amount),1)                      AS avg_order,
           SUM(return_flag)                          AS returns,
           ROUND(100.0*SUM(return_flag)/COUNT(*),1)  AS return_pct
    {BASE} AND retail_supplier IS NOT NULL
    GROUP BY retail_supplier ORDER BY revenue DESC
""")
if len(df_sup):
    st.dataframe(df_sup.style.format({
        "revenue":"₹{:,.0f}", "avg_order":"₹{:,.1f}", "return_pct":"{:.1f}%"
    }), use_container_width=True)
