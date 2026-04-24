"""
Smart-Boutique/pages/ML_ReturnPrediction.py
---------------------------------------------
Streamlit page for ML Model 1: Return / Cancellation Risk Prediction
"""

import os
import sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title="Return Risk · Smart Boutique",
    page_icon="🔄",
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
.risk-high   { background:#3b0d0d; border-left:4px solid #e74c3c;
               padding:1rem; border-radius:8px; }
.risk-medium { background:#3b2a0d; border-left:4px solid #f39c12;
               padding:1rem; border-radius:8px; }
.risk-low    { background:#0d3b2e; border-left:4px solid #2ecc71;
               padding:1rem; border-radius:8px; }
</style>
""", unsafe_allow_html=True)

st.markdown(f"<h1 style='color:{GOLD}'>🔄 Return & Cancellation Risk Predictor</h1>",
            unsafe_allow_html=True)
st.markdown("*ML Model 1 — Predicts whether an order is at risk of being returned or cancelled*")
st.divider()

# ── Check if model exists ─────────────────────────────────────────────────────
MODEL_PATH = os.path.join(ROOT, "ML", "return_model.pkl")
model_trained = os.path.exists(MODEL_PATH)

tab1, tab2, tab3 = st.tabs(["🎯 Predict Risk", "🏋️ Train Model", "📊 Model Performance"])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — PREDICT
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    if not model_trained:
        st.warning("⚠️ Model not trained yet. Go to the **Train Model** tab first.")
    else:
        st.subheader("Enter Order Details to Predict Return Risk")
        st.info("Fill in the order details below and click Predict to get the risk score.")

        c1, c2, c3 = st.columns(3)
        with c1:
            category = st.selectbox("Category",
                ["kurta", "set", "western dress", "top", "saree",
                 "blouse", "ethnic dress", "bottom"])
            size     = st.selectbox("Size", ["XS","S","M","L","XL","XXL","3XL","Free"])
            qty      = st.number_input("Quantity", min_value=1, max_value=20, value=1)
        with c2:
            amount   = st.number_input("Order Amount (₹)", min_value=0, max_value=50000, value=500)
            age      = st.number_input("Customer Age", min_value=10, max_value=100, value=30)
            season   = st.selectbox("Season", ["Spring","Summer","Autumn","Winter"])
        with c3:
            supplier = st.selectbox("Retail Supplier",
                ["Myntra", "Ajio", "Amazon", "Flipkart", "Meesho", "Nalli", "Other"])
            state    = st.text_input("Ship State (e.g. KERALA)", value="KERALA")
            b2b      = st.radio("Order Type", ["B2C", "B2B"], horizontal=True)

        predict_btn = st.button("🔮 Predict Return Risk", use_container_width=True)

        if predict_btn:
            try:
                from ML.return_prediction import predict_return_risk

                order_data = {
                    'category':        category,
                    'size':            size,
                    'qty':             qty,
                    'amount':          amount,
                    'age':             age,
                    'retail_supplier': supplier,
                    'ship_state':      state.upper(),
                    'b2b':             1 if b2b == "B2B" else 0,
                    'season':          season,
                    'price_per_unit':  round(amount / max(qty, 1), 2),
                    'weekend_order':   0,
                }

                result = predict_return_risk(order_data)

                if 'error' in result:
                    st.error(result['error'])
                else:
                    st.markdown("---")
                    st.subheader("🎯 Prediction Result")

                    risk_pct   = result['risk_pct']
                    risk_label = result['risk_label']
                    top_factors = result['top_factors']

                    # Risk gauge
                    col_gauge, col_info = st.columns([1, 2])
                    with col_gauge:
                        fig = go.Figure(go.Indicator(
                            mode="gauge+number",
                            value=risk_pct,
                            title={'text': "Return Risk %"},
                            gauge={
                                'axis': {'range': [0, 100]},
                                'bar': {'color': "#e74c3c" if risk_pct >= 60
                                        else "#f39c12" if risk_pct >= 30
                                        else "#2ecc71"},
                                'steps': [
                                    {'range': [0, 30],  'color': '#0d3b2e'},
                                    {'range': [30, 60], 'color': '#3b2a0d'},
                                    {'range': [60, 100],'color': '#3b0d0d'},
                                ],
                                'threshold': {
                                    'line': {'color': "white", 'width': 3},
                                    'thickness': 0.75,
                                    'value': risk_pct
                                }
                            },
                            number={'suffix': "%", 'font': {'color': GOLD}}
                        ))
                        fig.update_layout(
                            height=250,
                            paper_bgcolor="rgba(0,0,0,0)",
                            font_color="#aaa"
                        )
                        st.plotly_chart(fig, use_container_width=True)

                    with col_info:
                        st.markdown(f"### {risk_label}")

                        if risk_pct >= 60:
                            st.markdown(f"""
<div class='risk-high'>
<b>⚠️ High Return Risk — {risk_pct}%</b><br><br>
This order has a high chance of being returned or cancelled.<br>
<b>Recommended Action:</b> Call the customer to confirm measurements
and expectations before starting production.
</div>""", unsafe_allow_html=True)

                        elif risk_pct >= 30:
                            st.markdown(f"""
<div class='risk-medium'>
<b>⚡ Medium Return Risk — {risk_pct}%</b><br><br>
This order has a moderate return risk.<br>
<b>Recommended Action:</b> Send a WhatsApp confirmation with size chart
before dispatching.
</div>""", unsafe_allow_html=True)

                        else:
                            st.markdown(f"""
<div class='risk-low'>
<b>✅ Low Return Risk — {risk_pct}%</b><br><br>
This order is unlikely to be returned. Safe to proceed.<br>
<b>Recommended Action:</b> Process normally.
</div>""", unsafe_allow_html=True)

                        st.markdown(f"""
<br><b>🔍 Top Factors Influencing This Prediction:</b><br>
{'  '.join([f'`{f}`' for f in top_factors])}
""", unsafe_allow_html=True)

            except Exception as e:
                st.error(f"Prediction failed: {e}")
                st.info("Make sure the model is trained. Go to the Train Model tab.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — TRAIN
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.subheader("Train the Return Prediction Model")

    col_info, col_train = st.columns([2, 1])
    with col_info:
        st.markdown("""
**What this model learns:**
- Patterns in your historical orders that lead to returns/cancellations
- Which combinations of category, size, supplier, state are risky

**Training data used:**
- All orders from `boutique.db`
- Target: `return_flag` (1 = Returned or Cancelled, 0 = Delivered)
- Features: category, size, qty, amount, gender, age, supplier, state, b2b, season

**Algorithm:** HistGradientBoosting Classifier with class balancing
- Upgraded from RandomForest — AUC improved 0.61 → 0.68
- F1(return) improved 0.15 → 0.20 (catches more actual returns)
- Early stopping prevents overfitting on imbalanced data
        """)

        if model_trained:
            st.success("✅ Model is already trained and ready to use.")
            st.info("You can re-train anytime to update with new order data.")

    with col_train:
        st.markdown("<br>", unsafe_allow_html=True)
        train_btn = st.button("🏋️ Train Model Now", use_container_width=True,
                              type="primary")

    if train_btn:
        with st.spinner("🤖 Training in progress… this takes 20–40 seconds…"):
            try:
                from ML.return_prediction import train_model
                metrics = train_model()
                st.session_state['return_metrics'] = metrics
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
            import pickle
            META_PATH = os.path.join(ROOT, "ML", "return_model_meta.pkl")
            with open(META_PATH, 'rb') as f:
                meta = pickle.load(f)
            metrics = meta['metrics']

            # KPI row
            c1,c2,c3,c4,c5 = st.columns(5)
            c1.metric("🎯 Accuracy",        f"{metrics['accuracy']}%")
            c2.metric("📈 AUC-ROC Score",   f"{metrics['auc_roc']}")
            c3.metric("📊 Training Rows",   f"{int(metrics['total_rows']):,}")
            c4.metric("🔄 Return Rate",     f"{metrics['return_rate']}%")
            c5.metric("🤖 Algorithm",       "HistGradientBoosting")

            st.divider()
            col_fi, col_cm = st.columns(2)

            # Feature importance chart
            with col_fi:
                st.subheader("Feature Importance")
                fi_df = pd.DataFrame(
                    list(metrics['feature_importance'].items()),
                    columns=['Feature', 'Importance']
                ).sort_values('Importance', ascending=True)

                fig_fi = px.bar(fi_df, x='Importance', y='Feature',
                                orientation='h',
                                color='Importance',
                                color_continuous_scale='YlOrBr')
                fig_fi.update_layout(
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    font_color="#aaa", showlegend=False
                )
                st.plotly_chart(fig_fi, use_container_width=True)
                st.caption("Higher = more influential in predicting returns")

            # Confusion matrix
            with col_cm:
                st.subheader("Confusion Matrix")
                cm = metrics['confusion_matrix']
                cm_df = pd.DataFrame(
                    cm,
                    index=['Actual: Delivered', 'Actual: Returned'],
                    columns=['Predicted: Delivered', 'Predicted: Returned']
                )
                fig_cm = px.imshow(
                    cm_df,
                    text_auto=True,
                    color_continuous_scale='YlOrBr',
                    title="Confusion Matrix"
                )
                fig_cm.update_layout(
                    plot_bgcolor="#fefeff",
                    paper_bgcolor="#fcfcfc",
                    font_color="#000000"

                )
                st.plotly_chart(fig_cm, use_container_width=True)

            # Interpretation
            st.divider()
            st.subheader("📖 How to Read These Results")
            st.markdown(f"""
| Metric | Value | Meaning |
|---|---|---|
| **Accuracy** | {metrics['accuracy']}% | Out of 100 orders, the model correctly classifies this many |
| **AUC-ROC** | {metrics['auc_roc']} | 1.0 = perfect, 0.5 = random guess. Above 0.7 is good |
| **Precision (Return)** | {metrics['precision_return']} | When model says "return risk", it is right this % of the time |
| **Recall (Return)** | {metrics['recall_return']} | Out of all actual returns, model catches this fraction |

**Top risk factors in your data:**
""")
            top_features = sorted(
                metrics['feature_importance'].items(),
                key=lambda x: x[1], reverse=True
            )[:3]
            for i, (feat, score) in enumerate(top_features, 1):
                st.markdown(f"{i}. **`{feat}`** — contributes {score*100:.1f}% to the prediction")

            st.info(
                f"💡 **Algorithm:** {metrics.get('algorithm','HistGradientBoostingClassifier v2.0')}  \n"
                f"F1(return) = {metrics['f1_return']} | "
                f"Recall = {metrics['recall_return']} | "
                f"Precision = {metrics['precision_return']}"
            )

        except Exception as e:
            st.error(f"Could not load metrics: {e}")

st.divider()
st.caption("🔄 Return Risk Predictor · ML Model 1 · HistGradientBoosting Classifier v2.0 · Smart Boutique")
