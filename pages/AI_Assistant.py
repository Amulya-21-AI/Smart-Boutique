"""
Smart-Boutique/pages/AI_Assistant.py
"""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import streamlit as st
from database.db import init_db, run_query

st.set_page_config(page_title="AI Assistant · Smart Boutique", page_icon="🤖", layout="wide")
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
</style>
""", unsafe_allow_html=True)

st.markdown(f"<h1 style='color:{GOLD}'>🤖 AI & ML Integration Hub</h1>", unsafe_allow_html=True)
st.markdown("*Your database is ML-ready. Here is what is ready and what is coming.*")
st.divider()

# ── ML Readiness Check ────────────────────────────────────────────────────────
st.subheader("📊 ML Data Readiness Check")
readiness = run_query("""
    SELECT
        COUNT(*)                                                 AS total_rows,
        SUM(CASE WHEN season IS NOT NULL THEN 1 ELSE 0 END)     AS season_filled,
        SUM(CASE WHEN return_flag IS NOT NULL THEN 1 ELSE 0 END) AS return_flag_filled,
        SUM(CASE WHEN weekend_order IS NOT NULL THEN 1 ELSE 0 END) AS weekend_filled,
        SUM(CASE WHEN delivery_days IS NOT NULL THEN 1 ELSE 0 END) AS delivery_filled
    FROM orders
""")

if len(readiness):
    r = readiness.iloc[0]
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Total Training Rows",  f"{int(r['total_rows']        or 0):,}")
    c2.metric("Season Feature",       f"{int(r['season_filled']     or 0):,} rows ")
    c3.metric("Return Flag",          f"{int(r['return_flag_filled'] or 0):,} rows ")
    c4.metric("Delivery Days Filled", f"{int(r['delivery_filled']   or 0):,} rows")
    if int(r['delivery_filled'] or 0) == 0:
        st.warning("⚠️ **delivery_days** is empty — go to Orders → Update Status to fill it.")


st.divider()

# ── Planned Models ────────────────────────────────────────────────────────────
col1, col2 = st.columns(2)

with col1:
    st.subheader("🎯 Model 1: Delivery Day Prediction")
    st.markdown("""
**Type:** Regression (Random Forest / XGBoost)
**Target column:** `delivery_days`

**Features ready in your DB:**
- `category`, `size`, `qty`
- `ship_state`, `season`, `weekend_order`
- `retail_supplier`, `b2b`

**Status:** 🟡 Fill `delivery_days` via Orders page first
""")
    st.code("""
# ML/delivery_prediction.py
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
import pandas as pd
from database.db import run_query

df = run_query('''
    SELECT category, size, qty, ship_state,
           season, weekend_order, b2b, delivery_days
    FROM orders
    WHERE delivery_days IS NOT NULL
''')

X = pd.get_dummies(df.drop('delivery_days', axis=1))
y = df['delivery_days']
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

model = RandomForestRegressor(n_estimators=100)
model.fit(X_train, y_train)
print("Score:", model.score(X_test, y_test))
""", language="python")

with col2:
    st.subheader("🛍️ Model 2: Design Recommendation")
    st.markdown("""
**Type:** Collaborative Filtering / Content-Based
**Target:** Which design a customer will order next

**Features ready in your DB:**
- `cust_id`, `age_group`, `gender`
- `category`, `size`, `amount`
- `season`, `loyalty_tier`

**Status:** 🟡 Populate `designs` table with your catalog first
""")
    st.code("""
# ML/recommendation.py
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from database.db import run_query

def get_top_categories_for_customer(cust_id: int, top_n=3):
    return run_query(f'''
        SELECT category,
               COUNT(*) AS cnt,
               SUM(amount) AS spent
        FROM orders
        WHERE cust_id = {cust_id}
        GROUP BY category
        ORDER BY cnt DESC
        LIMIT {top_n}
    ''')
""", language="python")

st.divider()

# ── GenAI Preview ─────────────────────────────────────────────────────────────
st.subheader("✨ Coming Soon: AI Fashion Assistant (GenAI)")
st.markdown("""
- Answer customer questions about fabrics, styles, sizing
- Suggest outfits based on occasion and past orders
- Auto-generate design briefs for tailors
- Summarise order history in natural language

**Integration:** Anthropic Claude API · **Status:** 🔴 Planned
""")

with st.expander("💡 Preview: how the chat will look"):
    st.chat_message("user").write("I need a festive kurta for a wedding, size M")
    st.chat_message("assistant").write("""
Great choice! For a wedding I'd suggest a **Silk Festive Kurta in size M**.

Based on your order history, you prefer darker tones —
**Deep Burgundy** and **Royal Navy** would suit you well.

Your regular tailor **Rajan** (⭐ 4.8) is available and
specialises in kurtas. Estimated delivery: **5–7 days**.

Shall I book this for you?
""")

st.divider()
st.caption("🤖 Smart Boutique AI Hub · ML & GenAI features coming in the next phase")
