"""
Smart-Boutique/pages/ML_Recommendation.py
"""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import pickle

st.set_page_config(
    page_title="Recommendations · Smart Boutique",
    page_icon="🛍️",
    layout="wide"
)

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
[data-testid="metric-container"] {
    background: linear-gradient(135deg, #1a0a2e22, #0f346022);
    border: 1px solid #c9a96e44; border-radius: 12px; padding: 1rem;
}
.stButton > button {
    background: linear-gradient(135deg, #c9a96e, #e8c99a);
    color: #1a0a2e; font-weight: 600; border: none; border-radius: 8px;
}
.rec-card {
    background: linear-gradient(135deg, #1a0a2e, #16213e);
    border: 1px solid #c9a96e55;
    border-radius: 14px;
    padding: 1.5rem;
    margin-bottom: 1rem;
    transition: all 0.2s;
}
.rec-card-gold {
    background: linear-gradient(135deg, #2a1a0e, #1a100a);
    border: 2px solid #c9a96e;
    border-radius: 14px;
    padding: 1.5rem;
    margin-bottom: 1rem;
}
.confidence-bar-fill {
    height: 8px;
    border-radius: 4px;
    background: linear-gradient(90deg, #c9a96e, #e8c99a);
}
.confidence-bar-bg {
    height: 8px;
    border-radius: 4px;
    background: #ffffff11;
    margin-top: 0.5rem;
}
</style>
""", unsafe_allow_html=True)

st.markdown(f"<h1 style='color:{GOLD}'>🛍️ Design Recommendation Engine</h1>",
            unsafe_allow_html=True)
st.markdown("*ML Model 3 — Recommends the best product categories for each customer profile*")
st.divider()

MODEL_PATH = os.path.join(ROOT, "ML", "recommendation_model.pkl")
META_PATH  = os.path.join(ROOT, "ML", "recommendation_model_meta.pkl")
model_trained = os.path.exists(MODEL_PATH)

tab1, tab2, tab3, tab4 = st.tabs([
    "🎯 Get Recommendations",
    "👥 Customer Lookup",
    "🏋️ Train Model",
    "📊 Model Performance"
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — GET RECOMMENDATIONS
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    if not model_trained:
        st.warning("⚠️ Model not trained yet. Go to **Train Model** tab first.")
    else:
        st.subheader("Enter Customer Profile")
        st.info("Fill in the customer details to get personalised category recommendations.")

        c1, c2, c3 = st.columns(3)
        with c1:
            age     = st.number_input("Age", min_value=10, max_value=100, value=28)
            size    = st.selectbox("Usual Size",
                                   ["XS","S","M","L","XL","XXL","3XL","Free"])
            supplier = st.selectbox("Retail Supplier",
                                    ["Myntra","Ajio","Amazon","Flipkart","Meesho","Nalli","Other"])
        with c2:
            budget  = st.number_input("Budget / Avg Order (₹)",
                                      min_value=100, max_value=10000, value=800)
            season  = st.selectbox("Current Season",
                                   ["Spring","Summer","Autumn","Winter"])
            b2b     = st.radio("Order Type", ["B2C","B2B"], horizontal=True)
        with c3:
            top_n   = st.slider("Number of Recommendations", 1, 8, 5)
            st.markdown("<br>", unsafe_allow_html=True)
            rec_btn = st.button("✨ Get Recommendations",
                                use_container_width=True, type="primary")

        if rec_btn:
            try:
                from ML.recommendation import get_recommendations, get_popular_by_profile

                import datetime as _dt
                _month = _dt.date.today().month

                customer = {
                    'age':             age,
                    'size':            size,
                    'amount':          budget,
                    'season':          season,
                    'b2b':             1 if b2b == "B2B" else 0,
                    'retail_supplier': supplier,
                    'month_num':       _month,
                    'weekend_order':   0,
                    'price_per_unit':  budget,
                }

                recs = get_recommendations(customer, top_n=top_n)

                if recs and 'error' in recs[0]:
                    st.error(recs[0]['error'])
                else:
                    st.markdown("---")
                    st.subheader(f"✨ Top {len(recs)} Recommendations")

                    age_grp = (
                        "Teen" if age < 18 else
                        "Young Adult" if age < 30 else
                        "Adult" if age < 50 else "Senior"
                    )
                    st.markdown(
                        f"*Profile: {age} yrs ({age_grp}), "
                        f"Size {size}, Budget ₹{budget:,}, {season} · "
                        f"Boutique specialises in women's ethnic wear*"
                    )
                    st.markdown("<br>", unsafe_allow_html=True)

                    # Recommendation cards
                    for rec in recs:
                        card_class = 'rec-card-gold' if rec['rank'] == 1 else 'rec-card'
                        rank_badge = "🥇 Top Pick" if rec['rank'] == 1 else \
                                     "🥈 2nd Choice" if rec['rank'] == 2 else \
                                     f"#{rec['rank']}"

                        col_card, col_bar = st.columns([3, 1])
                        with col_card:
                            st.markdown(f"""
<div class='{card_class}'>
    <div style='display:flex; align-items:center; gap:1rem; margin-bottom:0.8rem;'>
        <span style='font-size:2.5rem;'>{rec['emoji']}</span>
        <div>
            <div style='font-size:1.3rem; font-weight:700; color:{GOLD};'>
                {rec['category'].title()}
                &nbsp;<span style='font-size:0.8rem; color:#888;
                background:#ffffff11; padding:2px 8px; border-radius:20px;'>
                {rank_badge}</span>
            </div>
            <div style='color:#aaa; font-size:0.9rem;'>{rec['description']}</div>
        </div>
    </div>
    <div style='display:grid; grid-template-columns:1fr 1fr 1fr; gap:0.5rem;
                font-size:0.85rem; color:#888;'>
        <div>📅 <b style='color:#ccc;'>Occasions:</b><br>{rec['occasions']}</div>
        <div>💰 <b style='color:#ccc;'>Price Range:</b><br>{rec['price_range']}</div>
        <div>👥 <b style='color:#ccc;'>Popular With:</b><br>{rec['popular_with']}</div>
    </div>
    <div class='confidence-bar-bg'>
        <div class='confidence-bar-fill'
             style='width:{min(rec["confidence"]*2, 100)}%;'></div>
    </div>
    <div style='font-size:0.8rem; color:#888; margin-top:0.3rem;'>
        Model confidence: {rec['confidence']}%
    </div>
</div>""", unsafe_allow_html=True)

                    # Confidence chart
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.subheader("📊 Recommendation Confidence")
                    rec_df = pd.DataFrame(recs)
                    fig = px.bar(
                        rec_df,
                        x='confidence', y='category',
                        orientation='h',
                        color='confidence',
                        color_continuous_scale='YlOrBr',
                        text='confidence',
                        labels={'confidence':'Confidence %','category':'Category'}
                    )
                    fig.update_traces(texttemplate='%{text:.1f}%',
                                      textposition='outside')
                    fig.update_layout(
                        plot_bgcolor="rgba(0,0,0,0)",
                        paper_bgcolor="rgba(0,0,0,0)",
                        font_color="#aaa",
                        yaxis=dict(autorange="reversed"),
                        showlegend=False,
                        coloraxis_showscale=False,
                        height=300
                    )
                    st.plotly_chart(fig, use_container_width=True)

                    # Historical popular for this profile
                    hist = get_popular_by_profile('W', age_grp, season)
                    if not hist.empty:
                        st.subheader("📜 Historically Popular for This Profile")
                        st.dataframe(hist.style.format({
                            'revenue': '₹{:,.0f}',
                            'avg_amount': '₹{:,.0f}'
                        }), use_container_width=True)

            except Exception as e:
                st.error(f"Recommendation failed: {e}")
                st.exception(e)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — CUSTOMER LOOKUP
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.subheader("Recommend for an Existing Customer")
    st.info("Look up a customer by ID and get personalised recommendations based on their profile.")

    search_col, btn_col = st.columns([3, 1])
    with search_col:
        cust_id = st.text_input("Enter Customer ID")
    with btn_col:
        st.markdown("<br>", unsafe_allow_html=True)
        lookup_btn = st.button("🔍 Look Up", use_container_width=True)

    if lookup_btn and cust_id:
        try:
            from database.db import run_query
            from ML.recommendation import get_recommendations

            # Fetch customer profile
            cust = run_query(f"""
                SELECT c.cust_id, c.name, c.gender, c.age, c.age_group,
                       c.loyalty_tier,
                       COUNT(o.order_id)   AS total_orders,
                       SUM(o.amount)       AS total_spent,
                       AVG(o.amount)       AS avg_order,
                       GROUP_CONCAT(DISTINCT o.category) AS categories_bought,
                       GROUP_CONCAT(DISTINCT o.size)     AS sizes_used
                FROM customers c
                LEFT JOIN orders o ON c.cust_id = o.cust_id
                WHERE c.cust_id = {cust_id}
                GROUP BY c.cust_id
            """)

            if cust.empty:
                st.warning(f"Customer ID {cust_id} not found.")
            else:
                row = cust.iloc[0]
                st.markdown(f"### 👤 {row.get('name', 'Customer')} — ID: {row['cust_id']}")

                m1,m2,m3,m4 = st.columns(4)
                m1.metric("Age",           row.get('age','—'))
                m2.metric("Age Group",     row.get('age_group','—'))
                m3.metric("Total Orders",  int(row.get('total_orders', 0)))
                m4.metric("Total Spent",   f"₹{float(row.get('total_spent',0) or 0):,.0f}")

                if row.get('categories_bought'):
                    st.markdown(f"**Past purchases:** {row['categories_bought']}")

                # Get avg order for budget estimate
                avg_amt = float(row.get('avg_order') or 800)

                # Determine current season
                import datetime
                month = datetime.date.today().month
                season_now = ('Spring' if month in (3,4,5) else
                              'Summer' if month in (6,7,8) else
                              'Autumn' if month in (9,10,11) else 'Winter')

                # Get size from past orders
                sizes = str(row.get('sizes_used','M')).split(',')
                size  = sizes[0] if sizes else 'M'

                customer = {
                    'age':             int(row.get('age', 30)),
                    'size':            size,
                    'amount':          avg_amt,
                    'season':          season_now,
                    'b2b':             0,
                    'retail_supplier': 'Myntra',
                    'month_num':       month,
                    'weekend_order':   0,
                    'price_per_unit':  avg_amt,
                }

                st.markdown("---")
                st.subheader("✨ Personalised Recommendations")
                recs = get_recommendations(customer, top_n=3)

                cols = st.columns(3)
                for i, rec in enumerate(recs):
                    with cols[i]:
                        st.markdown(f"""
<div class='rec-card'>
    <div style='font-size:2rem; text-align:center;'>{rec['emoji']}</div>
    <div style='text-align:center; font-weight:700; color:{GOLD};
                margin:0.5rem 0;'>{rec['category'].title()}</div>
    <div style='text-align:center; color:#aaa; font-size:0.85rem;'>
        {rec['description']}</div>
    <div style='text-align:center; margin-top:0.8rem;
                font-size:1.1rem; font-weight:600; color:#2ecc71;'>
        {rec['confidence']}% match</div>
</div>""", unsafe_allow_html=True)

        except Exception as e:
            st.error(f"Lookup failed: {e}")
            st.exception(e)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — TRAIN
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.subheader("Train the Recommendation Model")

    col_info, col_btn = st.columns([2, 1])
    with col_info:
        st.markdown("""
**Why Content-Based (not Collaborative Filtering)?**

92% of your customers have placed only 1 order. Collaborative filtering
needs many orders per customer to find "similar users". Content-based works
from the very first order using customer profile attributes.

**What the model learns:**
- Which categories women vs men prefer
- How age influences category choice
- Which sizes map to which categories
- How budget determines category preference
- Seasonal popularity patterns

**Algorithm:** Gradient Boosting Classifier v2.0
- Upgraded from RandomForest — Accuracy 75% → 84%, Macro-F1 51% → 57%
- Trained on Women-only oversampled dataset (all 8 categories balanced)
- Gender removed from features — boutique serves women's ethnic wear
**Target:** Product category (8 categories)
**Accuracy:** ~84% overall | Macro-F1: ~57% (recommends rare items better)
        """)
        if model_trained:
            st.success("✅ Model is trained and ready.")

    with col_btn:
        st.markdown("<br><br>", unsafe_allow_html=True)
        train_btn = st.button("🏋️ Train Model Now",
                              use_container_width=True, type="primary")

    if train_btn:
        with st.spinner("🤖 Training recommendation model — ~30 seconds…"):
            try:
                from ML.recommendation import train_model
                metrics = train_model()
                st.success(f"✅ Model trained! Accuracy: {metrics['accuracy']}%")
                st.rerun()
            except Exception as e:
                st.error(f"Training failed: {e}")
                st.exception(e)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — PERFORMANCE
# ══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.subheader("Model Performance")

    if not model_trained:
        st.info("Train the model first to see performance.")
    else:
        try:
            with open(META_PATH, 'rb') as f:
                meta = pickle.load(f)
            m = meta['metrics']

            # KPIs
            c1,c2,c3,c4 = st.columns(4)
            c1.metric("🎯 Overall Accuracy", f"{m['accuracy']}%")
            c2.metric("📊 Macro-F1",         f"{m.get('macro_f1','—')}%",
                      help="Average F1 across all 8 categories — higher = recommends rare items better")
            c3.metric("📦 Training Rows",    f"{int(m['total_rows']):,}")
            c4.metric("🏷️ Categories",       len(m['categories']))

            st.divider()
            col1, col2 = st.columns(2)

            # Feature importance
            with col1:
                st.subheader("What Drives Recommendations")
                fi_df = pd.DataFrame(
                    list(m['feature_importance'].items()),
                    columns=['Feature','Importance']
                ).sort_values('Importance', ascending=True)
                fig_fi = px.bar(fi_df, x='Importance', y='Feature',
                                orientation='h', color='Importance',
                                color_continuous_scale='YlOrBr')
                fig_fi.update_layout(
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    font_color="#aaa", showlegend=False
                )
                st.plotly_chart(fig_fi, use_container_width=True)

            # Per-category accuracy
            with col2:
                st.subheader("Accuracy per Category")
                cat_acc = m.get('cat_accuracy', {})
                if cat_acc:
                    acc_df = pd.DataFrame(
                        list(cat_acc.items()),
                        columns=['Category','Accuracy %']
                    ).sort_values('Accuracy %', ascending=True)
                    fig_acc = px.bar(
                        acc_df, x='Accuracy %', y='Category',
                        orientation='h', color='Accuracy %',
                        color_continuous_scale='YlOrBr',
                        text='Accuracy %'
                    )
                    fig_acc.update_traces(
                        texttemplate='%{text:.1f}%', textposition='outside')
                    fig_acc.update_layout(
                        plot_bgcolor="rgba(0,0,0,0)",
                        paper_bgcolor="rgba(0,0,0,0)",
                        font_color="#aaa", showlegend=False,
                        coloraxis_showscale=False
                    )
                    st.plotly_chart(fig_acc, use_container_width=True)

            # Category distribution
            st.subheader("📊 Training Data Category Distribution")
            dist = m.get('category_dist', {})
            if dist:
                dist_df = pd.DataFrame(
                    list(dist.items()), columns=['Category','Orders']
                ).sort_values('Orders', ascending=False)
                fig_dist = px.bar(
                    dist_df, x='Category', y='Orders',
                    color='Orders', color_continuous_scale='YlOrBr'
                )
                fig_dist.update_layout(
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    font_color="#aaa", showlegend=False
                )
                st.plotly_chart(fig_dist, use_container_width=True)

            st.divider()
            st.subheader("📖 How to Interpret Results")
            st.markdown(f"""
| Category | Why accuracy varies | Notes |
|---|---|---|
| **Kurta / Set** | Very high volume — clear signals | Top predicted categories |
| **Saree** | Distinct profile: Adult/Senior, high budget | Near-perfect recall |
| **Western Dress** | Clear signal: younger women, moderate budget | Good accuracy |
| **Blouse / Bottom** | Rare in raw data — fixed by oversampling | Now learnable |
| **Ethnic Dress** | Balanced after oversampling | Improved vs v1 |

**Overall {m['accuracy']}% accuracy** (↑ from ~70% with RandomForest).  
**Macro-F1 {m.get('macro_f1','—')}%** means rare categories like blouse and bottom
are now being recommended, not ignored.

ℹ️ Model trained on Women-only data. Gender input removed — boutique specialises
in women's ethnic wear and the balanced dataset ensures all 8 categories are recommended.
""")

        except Exception as e:
            st.error(f"Could not load metrics: {e}")

st.divider()
st.caption("🛍️ Design Recommendation Engine · ML Model 3 · Gradient Boosting Classifier v2.0 · Women's Ethnic Wear · Smart Boutique")
