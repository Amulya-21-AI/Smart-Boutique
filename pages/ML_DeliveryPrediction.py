"""
Smart-Boutique/pages/ML_DeliveryPrediction.py
"""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import pickle
import datetime

st.set_page_config(
    page_title="Delivery Prediction · Smart Boutique",
    page_icon="🚚",
    layout="wide"
)

from database.db import init_db
init_db()
from utils.auth import require_auth
role, cust_id = require_auth()   # both admin and customer

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
.delivery-card {
    background: linear-gradient(135deg, #1a0a2e, #16213e);
    border: 1px solid #c9a96e44;
    border-radius: 12px;
    padding: 1.5rem;
    text-align: center;
}
</style>
""", unsafe_allow_html=True)

st.markdown(f"<h1 style='color:{GOLD}'>🚚 Delivery Day Predictor</h1>",
            unsafe_allow_html=True)
st.markdown("*ML Model 2 — Predicts how many days an order will take to deliver*")
st.divider()

MODEL_PATH = os.path.join(ROOT, "ML", "delivery_model.pkl")
META_PATH  = os.path.join(ROOT, "ML", "delivery_model_meta.pkl")
model_trained = os.path.exists(MODEL_PATH)

tab1, tab2, tab3 = st.tabs(["🚚 Predict Delivery", "🏋️ Train Model", "📊 Model Performance"])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — PREDICT
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    if not model_trained:
        st.warning("⚠️ Model not trained yet. Go to the **Train Model** tab first.")
    else:
        st.subheader("Enter Order Details")
        st.info("Fill in the order details to get an estimated delivery time.")

        c1, c2, c3 = st.columns(3)
        with c1:
            category    = st.selectbox("Category",
                ["kurta","set","western dress","top","saree",
                 "blouse","ethnic dress","bottom"])
            size        = st.selectbox("Size", ["XS","S","M","L","XL","XXL","3XL","Free"])
            qty         = st.number_input("Quantity", min_value=1, max_value=20, value=1)
        with c2:
            amount      = st.number_input("Order Amount (₹)", min_value=0, max_value=50000, value=800)
            supplier    = st.selectbox("Retail Supplier",
                ["Myntra","Ajio","Amazon","Flipkart","Meesho","Nalli","Other"])
            season      = st.selectbox("Season", ["Spring","Summer","Autumn","Winter"])
        with c3:
            state       = st.text_input("Ship State (e.g. KERALA)", value="KERALA")
            b2b         = st.radio("Order Type", ["B2C","B2B"], horizontal=True)
            order_date  = st.date_input("Order Date", value=datetime.date.today())

        predict_btn = st.button("🔮 Predict Delivery Days", use_container_width=True)

        if predict_btn:
            try:
                from ML.delivery_prediction import predict_delivery_days

                weekend = 1 if order_date.weekday() >= 5 else 0

                order_data = {
                    'category':        category,
                    'size':            size,
                    'qty':             qty,
                    'amount':          amount,
                    'retail_supplier': supplier,
                    'ship_state':      state.upper(),
                    'b2b':             1 if b2b == "B2B" else 0,
                    'season':          season,
                    'weekend_order':   weekend,
                    'price_per_unit':  round(amount / max(qty, 1), 2),
                }

                result = predict_delivery_days(order_data)

                if 'error' in result:
                    st.error(result['error'])
                else:
                    st.markdown("---")
                    st.subheader("📦 Delivery Prediction Result")

                    pred_days   = result.get('estimated_days') or result.get('predicted_days') or result.get('days', 5)
                    speed_label = result['speed_label']
                    color       = result['color']
                    mae         = result['mae']
                    top_factors = result['top_factors']

                    # Estimate delivery date
                    est_date = order_date + datetime.timedelta(days=pred_days)
                    earliest = order_date + datetime.timedelta(days=max(1, pred_days - int(mae)))
                    latest   = order_date + datetime.timedelta(days=pred_days + int(mae))

                    # Result cards
                    col_days, col_date, col_speed = st.columns(3)

                    with col_days:
                        st.markdown(f"""
<div class='delivery-card'>
    <div style='font-size:3rem;'>📦</div>
    <div style='font-size:2.5rem; font-weight:700; color:{color};'>{pred_days}</div>
    <div style='color:#aaa;'>Estimated Days</div>
    <div style='color:#666; font-size:0.85rem;'>±{mae} days accuracy</div>
</div>""", unsafe_allow_html=True)

                    with col_date:
                        st.markdown(f"""
<div class='delivery-card'>
    <div style='font-size:3rem;'>📅</div>
    <div style='font-size:1.4rem; font-weight:700; color:{GOLD};'>
        {est_date.strftime('%d %b %Y')}
    </div>
    <div style='color:#aaa;'>Expected Delivery</div>
    <div style='color:#666; font-size:0.85rem;'>
        {earliest.strftime('%d %b')} – {latest.strftime('%d %b %Y')}
    </div>
</div>""", unsafe_allow_html=True)

                    with col_speed:
                        st.markdown(f"""
<div class='delivery-card'>
    <div style='font-size:3rem;'>⚡</div>
    <div style='font-size:1.6rem; font-weight:700; color:{color};'>{speed_label}</div>
    <div style='color:#aaa;'>Delivery Speed</div>
    <div style='color:#666; font-size:0.85rem;'>Based on your order profile</div>
</div>""", unsafe_allow_html=True)

                    st.markdown("<br>", unsafe_allow_html=True)

                    # Timeline visual
                    st.subheader("📅 Delivery Timeline")
                    timeline_data = {
                        'Event':  ['Order Placed', 'Processing',
                                   'Dispatched', 'Expected Delivery'],
                        'Day':    [0, 1, 2, pred_days],
                        'Date':   [
                            order_date.strftime('%d %b'),
                            (order_date + datetime.timedelta(1)).strftime('%d %b'),
                            (order_date + datetime.timedelta(2)).strftime('%d %b'),
                            est_date.strftime('%d %b')
                        ]
                    }
                    df_tl = pd.DataFrame(timeline_data)
                    fig_tl = px.scatter(df_tl, x='Day', y=[0]*4,
                                        text='Event', size=[15,12,12,15],
                                        color='Day',
                                        color_continuous_scale='YlOrBr')
                    fig_tl.update_traces(textposition='top center',
                                         marker=dict(symbol='circle'))
                    # Connect the dots
                    fig_tl.add_shape(type='line', x0=0, x1=pred_days,
                                     y0=0, y1=0,
                                     line=dict(color=GOLD, width=2, dash='dot'))
                    fig_tl.update_layout(
                        height=200,
                        yaxis=dict(visible=False, range=[-1, 1]),
                        xaxis=dict(title='Days from Order'),
                        showlegend=False,
                        coloraxis_showscale=False,
                        plot_bgcolor="rgba(0,0,0,0)",
                        paper_bgcolor="rgba(0,0,0,0)",
                        font_color="#aaa"
                    )
                    st.plotly_chart(fig_tl, use_container_width=True)

                    # Top factors
                    st.markdown(f"""
**🔍 Key factors affecting this delivery time:**
{' · '.join([f'`{f}`' for f in top_factors])}
""")
                    if result.get('data_source') == 'simulated':
                        st.caption("ℹ️ Model trained on simulated delivery data. "
                                   "Update actual delivery days in Orders page "
                                   "to improve accuracy over time.")

            except Exception as e:
                st.error(f"Prediction failed: {e}")
                st.exception(e)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — TRAIN
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.subheader("Train the Delivery Prediction Model")

    col_info, col_btn = st.columns([2, 1])
    with col_info:
        st.markdown("""
**What this model learns:**
- How long deliveries take based on location, supplier, season and order type
- Which states and suppliers consistently deliver faster or slower

**Training data:**
- All **Delivered** orders from your database
- If `delivery_days` is not yet filled → uses realistic simulation based on
  Indian logistics patterns (state distance, season, weekends)
- Once you fill real delivery days via Orders → Update Status,
  the model automatically uses real data on next train

**Algorithm:** HistGradientBoosting Regressor v2.0
- Upgraded from RandomForest — 6× faster, native missing-value handling
- Same MAE now (simulated data); improves significantly when real delivery days are recorded
**Target:** Number of days from order to delivery
        """)

        if model_trained:
            st.success("✅ Model is trained and ready.")
            # Show data source
            try:
                with open(META_PATH, 'rb') as f:
                    meta = pickle.load(f)
                source = meta['metrics'].get('data_source', 'simulated')
                if source == 'simulated':
                    st.warning("📊 Currently using **simulated** delivery data. "
                               "Fill real delivery days in Orders page for better accuracy.")
                else:
                    st.info("📊 Using **real** delivery data from your database.")
            except Exception:
                pass

    with col_btn:
        st.markdown("<br><br>", unsafe_allow_html=True)
        train_btn = st.button("🏋️ Train Model Now",
                              use_container_width=True, type="primary")

    if train_btn:
        with st.spinner("🤖 Training in progress — ~20 seconds…"):
            try:
                from ML.delivery_prediction import train_model
                metrics = train_model()
                st.session_state['delivery_metrics'] = metrics
                st.success("✅ Model trained and saved successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Training failed: {e}")
                st.exception(e)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — PERFORMANCE
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.subheader("Model Performance Metrics")

    if not model_trained:
        st.info("Train the model first to see performance metrics.")
    else:
        try:
            with open(META_PATH, 'rb') as f:
                meta = pickle.load(f)
            m = meta['metrics']

            # KPI row
            c1,c2,c3,c4,c5 = st.columns(5)
            c1.metric("📏 MAE",              f"{m['mae']} days",
                      help="Average prediction error in days")
            c2.metric("📐 RMSE",             f"{m['rmse']} days")
            c3.metric("📈 R² Score",         f"{m['r2_score']}",
                      help="1.0 = perfect, 0 = no better than average")
            c4.metric("📅 Avg Delivery",     f"{m['mean_delivery_days']} days")
            c5.metric("📦 Training Orders",  f"{int(m['total_rows']):,}")

            st.divider()

            col_fi, col_dist = st.columns(2)

            # Feature importance
            with col_fi:
                st.subheader("What Drives Delivery Time")
                fi_df = pd.DataFrame(
                    list(m['feature_importance'].items()),
                    columns=['Feature', 'Importance']
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

            # Prediction distribution
            with col_dist:
                st.subheader("Delivery Speed Distribution")
                dist = m.get('prediction_dist', {})
                if dist:
                    dist_df = pd.DataFrame(
                        list(dist.items()), columns=['Speed', 'Orders']
                    )
                    fig_d = px.pie(dist_df, values='Orders', names='Speed',
                                  color_discrete_sequence=[
                                      '#2ecc71','#c9a96e','#f39c12','#e74c3c'])
                    fig_d.update_layout(
                        plot_bgcolor="rgba(0,0,0,0)",
                        paper_bgcolor="rgba(0,0,0,0)",
                        font_color="#aaa"
                    )
                    st.plotly_chart(fig_d, use_container_width=True)

            # How to read results
            st.divider()
            st.subheader("📖 How to Read These Results")
            st.markdown(f"""
| Metric | Value | Meaning |
|---|---|---|
| **MAE** | {m['mae']} days | On average, prediction is off by {m['mae']} days |
| **RMSE** | {m['rmse']} days | Penalises larger errors more heavily |
| **R² Score** | {m['r2_score']} | How much variation the model explains (0–1) |
| **Avg Delivery** | {m['mean_delivery_days']} days | Average delivery time across all orders |

**Top delivery time factors:**
""")
            for i, (feat, score) in enumerate(
                sorted(m['feature_importance'].items(),
                       key=lambda x: x[1], reverse=True)[:3], 1):
                st.markdown(f"{i}. **`{feat}`** — {score*100:.1f}% influence")

            source = m.get('data_source', 'simulated')
            if source == 'simulated':
                st.info("💡 **Improve accuracy:** Go to Orders → Update Status → "
                        "fill 'Actual Delivery Days' for your orders, then re-train.")

        except Exception as e:
            st.error(f"Could not load metrics: {e}")

st.divider()
st.caption("🚚 Delivery Day Predictor · ML Model 2 · HistGradientBoosting Regressor v2.0 · Smart Boutique")
