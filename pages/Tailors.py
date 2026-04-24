"""
Smart-Boutique/pages/Tailors.py
"""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import streamlit as st
import datetime
from database.db import init_db, insert_tailor, get_all_tailors, run_update, run_query

st.set_page_config(page_title="Tailors · Smart Boutique", page_icon="✂️", layout="wide")
init_db()

GOLD = "#c9a96e"
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=DM+Sans:wght@300;400;500&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
h1,h2,h3 { font-family: 'Playfair Display', serif !important; }
section[data-testid="stSidebar"] {
    background: linear-gradient(160deg, #1a0a2e 0%, #16213e 60%, #0f3460 100%);
}
section[data-testid="stSidebar"] * { color: #f5e6d3 !important; }
.stButton > button {
    background: linear-gradient(135deg, #c9a96e, #e8c99a);
    color: #1a0a2e; font-weight: 600; border: none; border-radius: 8px;
}
</style>
""", unsafe_allow_html=True)

st.markdown(f"<h1 style='color:{GOLD}'>✂️ Tailor Management</h1>", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["➕ Add Tailor", "👥 Tailor Directory", "📊 Performance"])

# ── TAB 1: Add Tailor ─────────────────────────────────────────────────────────
with tab1:
    st.subheader("Register New Tailor")
    with st.form("tailor_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            t_name   = st.text_input("Full Name *")
            t_phone  = st.text_input("Phone Number (10 digits)")
            t_spec   = st.selectbox("Specialty *",
                                    ["kurta","set","western","saree","blouse","all"])
        with c2:
            t_exp    = st.number_input("Experience (years)", min_value=0, max_value=50, value=2)
            t_joined = st.date_input("Joining Date", value=datetime.date.today())
        t_submit = st.form_submit_button("✅ Add Tailor", use_container_width=True)

    if t_submit:
        if not t_name.strip():
            st.error("Name is required.")
        elif t_phone and (not t_phone.isdigit() or len(t_phone) != 10):
            st.error("Phone must be 10 digits.")
        else:
            tid = insert_tailor(t_name.strip(), t_phone.strip(),
                                t_spec, int(t_exp), str(t_joined))
            st.success(f"🎉 Tailor **{t_name}** added! Tailor ID: **{tid}**")

# ── TAB 2: Directory ──────────────────────────────────────────────────────────
with tab2:
    st.subheader("All Tailors")
    df = get_all_tailors()
    if df.empty:
        st.info("No tailors registered yet. Use the Add Tailor tab.")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Tailors",  len(df))
        c2.metric("Available",      len(df[df["availability"]=="Available"]))
        c3.metric("Avg Experience", f"{df['experience_yrs'].mean():.1f} yrs")

        st.dataframe(
            df[["tailor_id","name","specialty","experience_yrs",
                "rating","availability","joined_date"]],
            use_container_width=True
        )

        st.subheader("Update Availability / Rating")
        with st.form("avail_form"):
            sel_tailor = st.selectbox("Select Tailor", df["name"].tolist())
            new_avail  = st.selectbox("Availability", ["Available","Busy","On Leave"])
            new_rating = st.slider("Rating (0–5)", 0.0, 5.0, step=0.1)
            avail_sub  = st.form_submit_button("✅ Update")
        if avail_sub:
            tid_row = df[df["name"]==sel_tailor]["tailor_id"].values
            if len(tid_row):
                run_update(
                    "UPDATE tailors SET availability=?, rating=? WHERE tailor_id=?",
                    (new_avail, new_rating, int(tid_row[0]))
                )
                st.success(f"Updated **{sel_tailor}** → {new_avail}, Rating: {new_rating}")
                st.rerun()

# ── TAB 3: Performance ────────────────────────────────────────────────────────
with tab3:
    st.subheader("Tailor Performance Overview")
    df_perf = run_query("""
        SELECT t.name AS tailor, t.specialty, t.rating,
               COUNT(o.order_id)             AS total_orders,
               SUM(o.amount)                 AS total_revenue,
               ROUND(AVG(o.delivery_days),1) AS avg_delivery_days,
               SUM(o.return_flag)            AS returns
        FROM tailors t
        LEFT JOIN orders o ON t.tailor_id = o.tailor_id
        GROUP BY t.tailor_id
        ORDER BY total_orders DESC
    """)
    if df_perf.empty or df_perf["total_orders"].sum() == 0:
        st.info("Performance data appears once orders are assigned to tailors.")
    else:
        st.dataframe(df_perf.style.format({
            "total_revenue":"₹{:,.0f}", "avg_delivery_days":"{:.1f}"
        }), use_container_width=True)

        import plotly.express as px
        fig = px.scatter(df_perf, x="avg_delivery_days", y="rating",
                         size="total_orders", color="specialty",
                         hover_name="tailor",
                         title="Delivery Speed vs Rating")
        fig.update_layout(plot_bgcolor="rgba(0,0,0,0)",
                          paper_bgcolor="rgba(0,0,0,0)", font_color="#aaa")
        st.plotly_chart(fig, use_container_width=True)
