"""
Smart-Boutique/pages/ML_DemandForecast.py
"""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import pickle
import datetime

st.set_page_config(
    page_title="Demand Forecast · Smart Boutique",
    page_icon="📈",
    layout="wide"
)

GOLD    = "#c9a96e"
PALETTE = ["#c9a96e","#e8c99a","#e74c3c","#2ecc71",
           "#3498db","#9b59b6","#f39c12","#1abc9c"]


def hex_to_rgba(hex_color: str, alpha: float = 0.1) -> str:
    """Convert #c9a96e  →  rgba(201,169,110,0.1)"""
    hex_color = hex_color.lstrip('#')
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


MONTH_NAMES = ['Jan','Feb','Mar','Apr','May','Jun',
               'Jul','Aug','Sep','Oct','Nov','Dec']

FESTIVALS = {
    1:  ['Pongal','Makar Sankranti'],
    2:  ["Valentine's Day",'Maha Shivratri'],
    3:  ['Holi','Ugadi'],
    4:  ['Ram Navami','Baisakhi'],
    5:  ["Mother's Day",'Buddha Purnima'],
    6:  ['Eid al-Adha'],
    7:  ['Guru Purnima'],
    8:  ['Independence Day','Raksha Bandhan','Janmashtami'],
    9:  ['Ganesh Chaturthi','Navratri'],
    10: ['Dussehra','Karwa Chauth'],
    11: ['Diwali','Bhai Dooj'],
    12: ['Christmas','New Year Eve'],
}

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
.alert-card {
    border-radius: 10px; padding: 1rem; margin-bottom: 0.5rem;
    border-left: 4px solid #c9a96e;
    background: linear-gradient(135deg, #1a0a2e, #16213e);
}
.festival-badge {
    background: #c9a96e22; border: 1px solid #c9a96e44;
    border-radius: 20px; padding: 2px 10px;
    font-size: 0.8rem; color: #c9a96e;
    display: inline-block; margin: 2px;
}
</style>
""", unsafe_allow_html=True)

st.markdown(f"<h1 style='color:{GOLD}'>📈 Seasonal Demand Forecasting</h1>",
            unsafe_allow_html=True)
st.markdown("*ML Model 4 — Forecasts category demand for the next 6 months "
            "using seasonal patterns & Indian festival calendar*")
st.divider()

MODEL_PATH    = os.path.join(ROOT, "ML", "forecast_model.pkl")
META_PATH     = os.path.join(ROOT, "ML", "forecast_model_meta.pkl")
model_trained = os.path.exists(MODEL_PATH)

tab1, tab2, tab3, tab4 = st.tabs([
    "📅 6-Month Forecast",
    "🔔 Restock Alerts",
    "📊 Seasonal Patterns",
    "🏋️ Train & Performance",
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — 6-MONTH FORECAST
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    if not model_trained:
        st.warning("⚠️ Model not trained yet. Go to **Train & Performance** tab first.")
    else:
        st.subheader("Demand Forecast — Next 6 Months")

        c1, c2, c3 = st.columns(3)
        with c1:
            n_months  = st.slider("Months to forecast", 3, 12, 6)
        with c2:
            start_m   = st.selectbox("Starting from month",
                                     MONTH_NAMES,
                                     index=datetime.date.today().month - 1)
            start_num = MONTH_NAMES.index(start_m) + 1
        with c3:
            sel_cats  = st.multiselect(
                "Filter categories",
                ['kurta','set','western dress','top','saree',
                 'blouse','ethnic dress','bottom'],
                default=['kurta','set','western dress','top','saree']
            )

        try:
            from ML.demand_forecasting import forecast_next_months, get_full_year_actuals

            fc = forecast_next_months(n_months, start_month=start_num)

            fc_filtered = fc[fc['category'].isin(sel_cats)] if sel_cats else fc

            if fc_filtered.empty:
                st.info("No forecast data. Train the model first.")
            else:
                # ── KPI row ───────────────────────────────────────────────────
                total_units = int(fc_filtered['forecast_units'].sum())
                top_cat     = (fc_filtered.groupby('category')['forecast_units']
                                          .sum().idxmax())
                peak_row    = fc_filtered.loc[fc_filtered['forecast_units'].idxmax()]
                peak_month  = peak_row['month_name']
                peak_cat    = peak_row['category']

                k1, k2, k3, k4 = st.columns(4)
                k1.metric("📦 Total Forecast Units", f"{total_units:,}")
                k2.metric("🏆 Top Category",         top_cat.title())
                k3.metric("📅 Peak Month",            peak_month)
                k4.metric("🌟 Peak Category",         peak_cat.title())
                st.divider()

                # ── CHART 1: Line chart per category ─────────────────────────
                st.subheader("📊 Forecast by Category")
                month_order = fc_filtered['month_name'].unique().tolist()
                fig_line    = go.Figure()

                cats_to_plot = sel_cats if sel_cats else fc['category'].unique().tolist()
                for i, cat in enumerate(cats_to_plot):
                    cat_df = fc_filtered[fc_filtered['category'] == cat]
                    if cat_df.empty:
                        continue
                    color = PALETTE[i % len(PALETTE)]

                    # Confidence band — FIX 1: hex_to_rgba() instead of
                    # color.replace('#','rgba(') + ',0.08)'
                    fig_line.add_trace(go.Scatter(
                        x=cat_df['month_name'].tolist() +
                          cat_df['month_name'].tolist()[::-1],
                        y=cat_df['upper_bound'].tolist() +
                          cat_df['lower_bound'].tolist()[::-1],
                        fill='toself',
                        fillcolor=hex_to_rgba(color, 0.08),
                        line=dict(color='rgba(0,0,0,0)'),
                        showlegend=False,
                        hoverinfo='skip',
                    ))

                    # Forecast line
                    fig_line.add_trace(go.Scatter(
                        x=cat_df['month_name'],
                        y=cat_df['forecast_units'],
                        mode='lines+markers',
                        name=cat.title(),
                        line=dict(color=color, width=2),
                        marker=dict(size=7),
                        hovertemplate=(
                            f"<b>{cat.title()}</b><br>"
                            "Month: %{x}<br>"
                            "Forecast: %{y:,} units<extra></extra>"
                        ),
                    ))

                # FIX 2: festival markers as scatter text — not add_vline()
                # add_vline() crashes on categorical string x-axis
                upper_max = fc_filtered['upper_bound'].max()
                for month_name in month_order:
                    m_num = MONTH_NAMES.index(month_name) + 1
                    if FESTIVALS.get(m_num):
                        fig_line.add_trace(go.Scatter(
                            x=[month_name],
                            y=[upper_max * 1.08],
                            mode='text',
                            text=['🎉'],
                            textposition='top center',
                            showlegend=False,
                            hovertemplate=(
                                f"<b>{month_name}</b><br>"
                                + "<br>".join(FESTIVALS[m_num])
                                + "<extra></extra>"
                            ),
                        ))

                fig_line.update_layout(
                    height=420,
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    font_color="#aaa",
                    legend=dict(orientation="h", y=-0.15),
                    xaxis_title="Month",
                    yaxis_title="Forecast Units",
                    hovermode="x unified",
                )
                st.plotly_chart(fig_line, use_container_width=True)
                st.caption("🎉 = major Indian festival month | "
                           "Shaded area = confidence interval (±MAE×1.5)")

                # ── CHART 2: Stacked bar ──────────────────────────────────────
                st.subheader("📦 Total Demand per Month (All Categories)")
                monthly_total = (fc_filtered
                                 .groupby(['month_name','category'])['forecast_units']
                                 .sum().reset_index())

                fig_bar = px.bar(
                    monthly_total,
                    x='month_name', y='forecast_units',
                    color='category',
                    color_discrete_sequence=PALETTE,
                    barmode='stack',
                    labels={'forecast_units':'Units','month_name':'Month',
                            'category':'Category'},
                    text_auto=False,
                )
                fig_bar.update_layout(
                    height=380,
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    font_color="#aaa",
                    legend=dict(orientation="h", y=-0.15),
                )
                st.plotly_chart(fig_bar, use_container_width=True)

                # ── Forecast Table ────────────────────────────────────────────
                st.subheader("📋 Forecast Detail Table")
                pivot = fc_filtered.pivot_table(
                    index='category',
                    columns='month_name',
                    values='forecast_units',
                    aggfunc='sum',
                ).fillna(0).astype(int)

                ordered_cols   = [m for m in MONTH_NAMES if m in pivot.columns]
                pivot          = pivot[ordered_cols]
                pivot['Total'] = pivot.sum(axis=1)
                pivot          = pivot.sort_values('Total', ascending=False)

                st.dataframe(
                    pivot.style
                         .background_gradient(cmap='YlOrBr', axis=None)
                         .format("{:,}"),
                    use_container_width=True,
                )

                # ── Festival calendar ─────────────────────────────────────────
                st.subheader("🗓️ Festival Calendar for Forecast Period")
                for month_name in month_order:
                    m_num = MONTH_NAMES.index(month_name) + 1
                    fests = FESTIVALS.get(m_num, [])
                    if fests:
                        badges = ' '.join(
                            f"<span class='festival-badge'>{f}</span>"
                            for f in fests
                        )
                        st.markdown(f"**{month_name}** &nbsp; {badges}",
                                    unsafe_allow_html=True)

        except Exception as e:
            st.error(f"Forecast failed: {e}")
            st.exception(e)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — RESTOCK ALERTS
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.subheader("🔔 Restock Alerts — What to Stock Up On")

    if not model_trained:
        st.warning("Train the model first.")
    else:
        try:
            from ML.demand_forecasting import forecast_next_months, get_restock_alerts

            fc_all    = forecast_next_months(6)
            alerts_df = get_restock_alerts(fc_all, threshold_pct=0.10)

            today      = datetime.date.today()
            curr_month = MONTH_NAMES[today.month - 1]
            next_m_idx = today.month % 12
            next_month = MONTH_NAMES[next_m_idx]
            next_fests = FESTIVALS.get(next_m_idx + 1, [])

            st.markdown(f"**Current month:** {curr_month} &nbsp;|&nbsp; "
                        f"**Next month:** {next_month}")
            if next_fests:
                badges = ' '.join(
                    f"<span class='festival-badge'>{f}</span>"
                    for f in next_fests
                )
                st.markdown(f"🎉 Upcoming festivals: {badges}",
                            unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)

            if not alerts_df.empty:
                for _, row in alerts_df.iterrows():
                    color = ("#e74c3c" if '🔴' in row['alert']
                             else "#f39c12" if '🟡' in row['alert']
                             else "#2ecc71")
                    arrow = "▲" if row['change_pct'] > 0 else "▼"
                    st.markdown(f"""
<div class='alert-card' style='border-left-color:{color};'>
    <div style='display:flex;justify-content:space-between;align-items:center;'>
        <div>
            <span style='font-size:1.1rem;font-weight:700;color:{GOLD};'>
                {row['category'].title()}
            </span>
            &nbsp;<span style='color:{color};'>{row['alert']}</span>
        </div>
        <div style='text-align:right;'>
            <span style='font-size:1.3rem;color:{color};font-weight:700;'>
                {arrow} {abs(row['change_pct']):.1f}%
            </span><br>
            <span style='color:#aaa;font-size:0.85rem;'>
                {int(row['current']):,} → {int(row['next_month']):,} units
            </span>
        </div>
    </div>
</div>""", unsafe_allow_html=True)

            # 3-month heatmap
            st.subheader("📊 Next 3 Months Demand Heatmap")
            fc3    = forecast_next_months(3, start_month=today.month)
            pivot3 = fc3.pivot_table(
                index='category', columns='month_name',
                values='forecast_units', aggfunc='sum',
            ).fillna(0).astype(int)

            fig_heat = px.imshow(
                pivot3,
                text_auto=True,
                color_continuous_scale='YlOrBr',
                labels={'color':'Units'},
            )
            fig_heat.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font_color="#aaa",
            )
            st.plotly_chart(fig_heat, use_container_width=True)

            # Buying recommendations
            st.subheader("💡 Buying Recommendations")
            top_alert = alerts_df[alerts_df['change_pct'] > 10]
            if not top_alert.empty:
                for _, row in top_alert.iterrows():
                    extra = int(row['next_month'] - row['current'])
                    st.markdown(
                        f"- **{row['category'].title()}** — Order "
                        f"**{extra:,} extra units** for {next_month}. "
                        f"Demand rising by {row['change_pct']:.1f}%."
                    )
            else:
                st.success("✅ Demand is stable across all categories next month. "
                           "No urgent restocking needed.")

        except Exception as e:
            st.error(f"Alert generation failed: {e}")
            st.exception(e)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — SEASONAL PATTERNS
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.subheader("🌸 Seasonal Pattern Analysis")

    if not model_trained:
        st.warning("Train the model first.")
    else:
        try:
            from ML.demand_forecasting import (get_full_year_actuals,
                                               SEASONAL_PATTERNS, MONTH_NAMES)
            full_df = get_full_year_actuals()

            if full_df.empty:
                st.info("No data available.")
            else:
                # Full year heatmap
                st.subheader("📊 Full Year Demand Heatmap")
                pivot_full = full_df.pivot_table(
                    index='category', columns='month',
                    values='units', aggfunc='sum',
                ).fillna(0).astype(int)
                pivot_full.columns = [MONTH_NAMES[m - 1]
                                      for m in pivot_full.columns]

                fig_full = px.imshow(
                    pivot_full,
                    text_auto=True,
                    color_continuous_scale='YlOrBr',
                    aspect='auto',
                    labels={'color':'Units','x':'Month','y':'Category'},
                )
                fig_full.update_layout(
                    height=400,
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    font_color="#aaa",
                )
                st.plotly_chart(fig_full, use_container_width=True)
                st.caption("Darker = higher demand. Real data: Apr, May, Jun. "
                           "Other months: Indian seasonal pattern estimates.")

                # Seasonal index
                st.subheader("📈 Seasonal Index per Category")
                si_rows = []
                for cat, indices in SEASONAL_PATTERNS.items():
                    for i, idx in enumerate(indices):
                        si_rows.append({
                            'Category':       cat.title(),
                            'Month':          MONTH_NAMES[i],
                            'Seasonal Index': idx,
                        })
                si_df = pd.DataFrame(si_rows)

                fig_si = px.line(
                    si_df, x='Month', y='Seasonal Index',
                    color='Category',
                    color_discrete_sequence=PALETTE,
                    markers=True,
                    title="Seasonal Index (1.0 = average, >1.0 = high demand)",
                )
                fig_si.add_hline(y=1.0, line_dash="dash",
                                 line_color="#ffffff44",
                                 annotation_text="Average")
                fig_si.update_layout(
                    height=420,
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    font_color="#aaa",
                    legend=dict(orientation="h", y=-0.2),
                )
                st.plotly_chart(fig_si, use_container_width=True)

                # Season summary
                st.subheader("🍂 Demand by Season")
                season_sum = (full_df
                              .groupby(['season','category'])['units']
                              .sum().reset_index())
                fig_sea = px.bar(
                    season_sum, x='season', y='units',
                    color='category',
                    color_discrete_sequence=PALETTE,
                    barmode='group',
                    labels={'units':'Total Units','season':'Season',
                            'category':'Category'},
                )
                fig_sea.update_layout(
                    height=380,
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    font_color="#aaa",
                    legend=dict(orientation="h", y=-0.2),
                )
                st.plotly_chart(fig_sea, use_container_width=True)

        except Exception as e:
            st.error(f"Pattern analysis failed: {e}")
            st.exception(e)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — TRAIN & PERFORMANCE
# ══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.subheader("Train the Demand Forecasting Model")

    col_info, col_btn = st.columns([2, 1])
    with col_info:
        st.markdown("""
**How this model works:**

Your data covers only 3 months (Apr–Jun 2022). A standard time-series
model like ARIMA needs at least 2 full years of data. So we use a smarter approach:

1. **Real data anchor** — Apr, May, Jun 2022 actual order counts
2. **Indian seasonal patterns** — Well-known demand indices for each
   category based on festivals, weddings, and school/college calendar
3. **Gradient Boosting** — Learns from both real and pattern data
4. **Forecast with confidence intervals** — Predicts ±range per category

**As you record more months of real data**, the model automatically
uses real patterns and becomes more accurate.

**Algorithm:** Gradient Boosting Regressor v2.0
- Tuned: subsample=0.8, min_samples_leaf=3 for small 96-row dataset
- 3 new features added: `category_rank`, `is_festival_month`, `is_peak_season`
**Features:** Month (cyclic), season, lag values, rolling average, festival count,
festival month flag, peak season flag, category demand rank
        """)

        if model_trained:
            st.success("✅ Model is trained and ready.")
            try:
                with open(META_PATH, 'rb') as f:
                    meta = pickle.load(f)
                m = meta['metrics']
                st.info(
                    f"📊 Real data from months: "
                    f"{[MONTH_NAMES[x - 1] for x in m['real_months']]}  \n"
                    f"MAE: {m['mae']} units per category per month"
                )
            except Exception:
                pass

    with col_btn:
        st.markdown("<br><br>", unsafe_allow_html=True)
        train_btn = st.button("🏋️ Train Model Now",
                              use_container_width=True, type="primary")

    if train_btn:
        with st.spinner("🤖 Building seasonal model — ~20 seconds…"):
            try:
                from ML.demand_forecasting import train_model
                metrics = train_model()
                st.success(f"✅ Model trained! MAE: {metrics['mae']} units")
                st.rerun()
            except Exception as e:
                st.error(f"Training failed: {e}")
                st.exception(e)

    if model_trained:
        st.divider()
        st.subheader("📊 Model Performance")
        try:
            with open(META_PATH, 'rb') as f:
                meta = pickle.load(f)
            m = meta['metrics']

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("📏 MAE",           f"{m['mae']} units",
                      help="Average error per category per month")
            c2.metric("📦 Training Rows", f"{m['total_rows']}")
            c3.metric("🗓️ Real Months",   str(len(m['real_months'])))
            c4.metric("🏷️ Categories",    len(m['categories']))

            fi_df = (pd.DataFrame(list(m['feature_importance'].items()),
                                  columns=['Feature','Importance'])
                       .sort_values('Importance', ascending=True))

            fig_fi = px.bar(
                fi_df, x='Importance', y='Feature',
                orientation='h', color='Importance',
                color_continuous_scale='YlOrBr',
            )
            fig_fi.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font_color="#aaa",
                showlegend=False,
            )
            st.plotly_chart(fig_fi, use_container_width=True)

            st.subheader("📖 How to Read This")
            st.markdown(f"""
| Metric | Value | Meaning |
|---|---|---|
| **MAE** | {m['mae']} units | Prediction is off by {m['mae']} units per category per month |
| **Rolling Average** | Top feature | Recent months heavily predict next month |
| **Category rank** | New feature | Popular categories (set/kurta) have higher base demand |
| **Festival month** | New feature | Months with 2+ festivals get demand boost |
| **Peak season flag** | New feature | Oct/Nov/Sep flagged as Diwali peak season |
| **Lag values** | Supporting feature | Last month's demand informs next month |

**Top demand month per category:**
""")
            for cat, peak_m in m.get('peak_months', {}).items():
                st.markdown(
                    f"- **{cat.title()}** → peaks in "
                    f"**{MONTH_NAMES[peak_m - 1]}**"
                    f"  🎉 {', '.join(FESTIVALS.get(peak_m, []))}"
                )

        except Exception as e:
            st.error(f"Could not load metrics: {e}")

st.divider()
st.caption("📈 Seasonal Demand Forecasting · ML Model 4 · "
           "Gradient Boosting + Indian Seasonal Patterns · Smart Boutique")
