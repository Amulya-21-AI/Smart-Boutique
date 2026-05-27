"""pages/My_Profile.py — Customer personal dashboard"""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import streamlit as st
from database.db import init_db, run_query, get_orders_for_customer

st.set_page_config(page_title="My Profile · AMK Fashion Hub",
                   page_icon="👤", layout="wide")
init_db()

from utils.auth import require_auth, GOLD

role, cust_id = require_auth(['customer', 'admin'])

# ── Helpers ───────────────────────────────────────────────────────────────────
STATUS_STYLES = {
    "Delivered": ("🟢", "#2ecc71", "#0d3b2e"),
    "Shipped":   ("🔵", "#3498db", "#0d2a3b"),
    "Pending":   ("🟣", "#9b59b6", "#1a1a3b"),
    "Cancelled": ("🔴", "#e74c3c", "#3b0d0d"),
    "Returned":  ("🟡", "#f39c12", "#3b2a0d"),
}

PROGRESS_MAP = {
    "Pending":   ("In Queue",      20,  "#9b59b6"),
    "Shipped":   ("Work in Progress", 60, "#3498db"),
    "Delivered": ("Ready / Done",  100, "#2ecc71"),
    "Cancelled": ("Cancelled",       0, "#e74c3c"),
    "Returned":  ("Returned",         0, "#f39c12"),
}

def status_badge(s):
    emoji, color, bg = STATUS_STYLES.get(s, ("⚪", "#aaa", "#222"))
    return (f"<span style='background:{bg};color:{color};border:1px solid {color}44;"
            f"border-radius:20px;padding:2px 10px;font-size:0.8rem;font-weight:600;"
            f"white-space:nowrap;'>{emoji} {s}</span>")

def loyalty_badge(tier):
    badges = {
        "Gold":   ("🥇", "#c9a96e", "#2a1a0e"),
        "Silver": ("🥈", "#b0b8c1", "#1a1f24"),
        "Bronze": ("🥉", "#cd7f32", "#1f1208"),
    }
    icon, color, bg = badges.get(tier, ("", "#aaa", "#222"))
    return (f"<span style='background:{bg};color:{color};border:1px solid {color}55;"
            f"border-radius:20px;padding:2px 10px;font-size:0.8rem;font-weight:600;'>"
            f"{icon} {tier}</span>") if tier in badges else f"<span style='color:#aaa'>{tier or '—'}</span>"

# ── Resolve cust_id (admin can view any customer) ─────────────────────────────
if role == 'admin':
    st.markdown(f"<h1 style='color:{GOLD}'>👤 Customer Profile Viewer</h1>",
                unsafe_allow_html=True)
    search_id = st.text_input("Enter Customer ID to view", placeholder="e.g. 1042")
    if search_id.strip().isdigit():
        view_cust_id = int(search_id.strip())
    else:
        st.info("Enter a numeric Customer ID above.")
        st.stop()
else:
    view_cust_id = cust_id
    st.markdown(f"<h1 style='color:{GOLD}'>👤 My Profile</h1>",
                unsafe_allow_html=True)

# ── Load customer ─────────────────────────────────────────────────────────────
cust_df = run_query(
    "SELECT * FROM customers WHERE cust_id=?", (view_cust_id,)
)
if cust_df.empty:
    st.error("Customer not found.")
    st.stop()

cust = cust_df.iloc[0]

# ══════════════════════════════════════════════════════════════════════════════
# PROFILE CARD
# ══════════════════════════════════════════════════════════════════════════════
tier_html = loyalty_badge(cust.get('loyalty_tier', 'Bronze'))

st.markdown(f"""
<div style='background:linear-gradient(135deg,#1a0a2e,#16213e);
            border:1px solid #c9a96e44;border-radius:16px;padding:1.5rem;
            margin-bottom:1.5rem;'>
  <div style='display:flex;align-items:center;gap:1rem;flex-wrap:wrap;'>
    <div style='font-size:3rem;'>👗</div>
    <div style='flex:1;'>
      <div style='font-size:1.5rem;font-weight:700;color:#f5e6d3;'>
        {cust['name']}</div>
      <div style='color:#c9a96e;font-size:0.95rem;margin:4px 0;'>
        Customer ID: <strong>CUST-{cust['cust_id']}</strong>
        &nbsp;·&nbsp; {tier_html}
      </div>
      <div style='color:#aaa;font-size:0.85rem;'>
        📞 {cust.get('phone','—')} &nbsp;·&nbsp;
        ✉️ {cust.get('email','—')} &nbsp;·&nbsp;
        📍 {cust.get('city','—')}, {cust.get('state','KERALA')}
      </div>
      <div style='color:#888;font-size:0.8rem;margin-top:4px;'>
        Member since: {str(cust.get('created_at',''))[:10]}
      </div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Load orders ───────────────────────────────────────────────────────────────
orders = get_orders_for_customer(view_cust_id)

# ── Summary KPIs ─────────────────────────────────────────────────────────────
k1, k2, k3, k4 = st.columns(4)
k1.metric("Total Orders",     f"{len(orders):,}")
k2.metric("Total Spent",      f"₹{orders['amount'].sum():,.0f}" if not orders.empty else "₹0")
k3.metric("Active Orders",    int((orders['status'].isin(['Pending','Shipped'])).sum()) if not orders.empty else 0)
k4.metric("Completed Orders", int((orders['status'] == 'Delivered').sum()) if not orders.empty else 0)

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════════
tab_orders, tab_track, tab_tailor = st.tabs(
    ["📦 My Orders", "📍 Track & Progress", "✂️ My Tailor"]
)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — ORDER LIST
# ─────────────────────────────────────────────────────────────────────────────
with tab_orders:
    if orders.empty:
        st.info("You have no orders yet. Place your first order from the **Place / Track Order** page.")
        if st.button("📦 Place an Order"):
            st.switch_page("pages/Orders.py")
    else:
        # Filter
        fc1, fc2 = st.columns(2)
        with fc1:
            f_status = st.multiselect("Filter by Status",
                                       orders['status'].dropna().unique().tolist(),
                                       default=orders['status'].dropna().unique().tolist(),
                                       key="prof_status")
        with fc2:
            f_cat = st.multiselect("Filter by Category",
                                    orders['category'].dropna().unique().tolist(),
                                    default=orders['category'].dropna().unique().tolist(),
                                    key="prof_cat")

        filtered = orders.copy()
        if f_status: filtered = filtered[filtered['status'].isin(f_status)]
        if f_cat:    filtered = filtered[filtered['category'].isin(f_cat)]

        st.caption(f"Showing {len(filtered):,} of {len(orders):,} orders")

        for _, row in filtered.iterrows():
            badge = status_badge(row.get('status', ''))
            is_pickup = (not row.get('b2b') and
                         not str(row.get('ship_city', '')).strip())

            with st.expander(
                f"{'🏠' if is_pickup else '🚚'} {row['order_id']} "
                f"· {row['category'].title()} · ₹{float(row['amount']):,.0f} "
                f"· {row.get('order_date','')}",
                expanded=False
            ):
                d1, d2, d3 = st.columns(3)
                d1.markdown(f"**Category:** {row['category'].title()}  \n"
                            f"**Size:** {row.get('size','—')} | Qty: {row.get('qty',1)}")
                d2.markdown(f"**Amount:** ₹{float(row['amount']):,.0f}  \n"
                            f"**Order Date:** {row.get('order_date','—')}")
                d3.markdown(f"**Delivery Date:** {row.get('delivery_date','—') or '—'}  \n"
                            f"**Supplier:** {row.get('retail_supplier','—') or '—'}")
                st.markdown(f"**Status:** {badge}", unsafe_allow_html=True)

                if is_pickup:
                    st.info("🏠 **Walk-in / Pickup Order** — no shipping required.")

# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 — TRACK & PROGRESS
# ─────────────────────────────────────────────────────────────────────────────
with tab_track:
    if orders.empty:
        st.info("No orders to track yet.")
    else:
        active = orders[orders['status'].isin(['Pending', 'Shipped'])].copy()
        if active.empty:
            st.success("All your orders have been completed or cancelled.")
        else:
            st.markdown(f"#### Tracking {len(active)} active order(s)")

        for _, row in orders.iterrows():
            status    = row.get('status', 'Pending')
            label, pct, bar_color = PROGRESS_MAP.get(status, ("Unknown", 0, "#aaa"))
            is_pickup = (not row.get('b2b') and
                         not str(row.get('ship_city', '')).strip())
            est_days  = row.get('estimated_days') or row.get('delivery_days')
            tailor    = row.get('tailor_name') or None

            st.markdown(f"""
<div style='background:#1a0a2e;border:1px solid #c9a96e33;border-radius:12px;
            padding:1.2rem;margin-bottom:1rem;'>
  <div style='display:flex;justify-content:space-between;align-items:center;
              flex-wrap:wrap;gap:0.5rem;margin-bottom:0.8rem;'>
    <div>
      <span style='color:#c9a96e;font-weight:600;'>{row['order_id']}</span>
      &nbsp;·&nbsp;
      <span style='color:#f5e6d3;'>{str(row.get('category','')).title()}</span>
    </div>
    <div style='color:#888;font-size:0.85rem;'>{row.get('order_date','')}</div>
  </div>
  <div style='margin-bottom:0.6rem;'>
    <div style='display:flex;justify-content:space-between;
                font-size:0.8rem;color:#aaa;margin-bottom:4px;'>
      <span>Work Progress</span><span>{label}</span>
    </div>
    <div style='background:#ffffff15;border-radius:999px;height:8px;overflow:hidden;'>
      <div style='width:{pct}%;background:{bar_color};height:100%;
                  border-radius:999px;transition:width 0.4s;'></div>
    </div>
  </div>
  {'<div style="color:#9b59b6;font-size:0.85rem;">⏳ Your order is in the queue — work will begin soon.</div>' if status == 'Pending' else ''}
  {'<div style="color:#3498db;font-size:0.85rem;">🪡 Our tailor is currently working on your outfit.</div>' if status == 'Shipped' else ''}
  {'<div style="color:#2ecc71;font-size:0.85rem;">✅ Your order is ready / delivered.</div>' if status == 'Delivered' else ''}
  {f'<div style="color:#c9a96e;font-size:0.85rem;margin-top:6px;">✂️ Assigned Tailor: <strong>{tailor}</strong></div>' if tailor else ''}
  {f'<div style="color:#3498db;font-size:0.85rem;margin-top:6px;">🚚 Estimated delivery: {est_days} days from order date.</div>' if est_days and not is_pickup else ''}
  {f'<div style="color:#f39c12;font-size:0.85rem;margin-top:6px;">🏠 Pickup Order — please visit the boutique in approx. {est_days or "7–10"} days.</div>' if is_pickup and status not in ("Delivered","Cancelled") else ''}
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 3 — MY TAILOR
# ─────────────────────────────────────────────────────────────────────────────
with tab_tailor:
    if orders.empty:
        st.info("No orders yet — a tailor will be assigned when you place an order.")
    else:
        tailor_orders = orders[orders['tailor_id'].notna()].copy()

        if tailor_orders.empty:
            st.info("No tailor has been assigned to your orders yet. "
                    "The boutique will assign a tailor once your order is confirmed.")
        else:
            # Show unique tailors assigned to this customer
            seen = set()
            for _, row in tailor_orders.iterrows():
                tid = row.get('tailor_id')
                if tid and tid not in seen:
                    seen.add(tid)
                    tname   = row.get('tailor_name', '—')
                    tphone  = row.get('tailor_phone', '—')
                    tspec   = row.get('tailor_specialty', '—')

                    st.markdown(f"""
<div style='background:linear-gradient(135deg,#1a0a2e,#16213e);
            border:1px solid #c9a96e44;border-radius:14px;padding:1.4rem;
            margin-bottom:1rem;'>
  <div style='font-size:1.1rem;font-weight:700;color:#c9a96e;margin-bottom:0.8rem;'>
    ✂️ {tname}
  </div>
  <div style='color:#f5e6d3;'>📞 <a href='tel:{tphone}'
    style='color:#c9a96e;text-decoration:none;font-weight:600;'>{tphone}</a>
  </div>
  <div style='color:#aaa;font-size:0.85rem;margin-top:4px;'>
    Specialty: {tspec}
  </div>
  <div style='color:#888;font-size:0.8rem;margin-top:0.8rem;
              padding:0.6rem;background:#ffffff08;border-radius:8px;'>
    📌 You can call or visit the boutique to speak with your tailor directly.
    Boutique contact: <strong style='color:#c9a96e;'>9876543210</strong>
  </div>
</div>
""", unsafe_allow_html=True)

                    # Orders assigned to this tailor
                    this_tailor_orders = tailor_orders[tailor_orders['tailor_id'] == tid]
                    st.caption(f"Orders with {tname}:")
                    for _, o in this_tailor_orders.iterrows():
                        badge = status_badge(o.get('status', ''))
                        st.markdown(
                            f"&nbsp;&nbsp;• `{o['order_id']}` "
                            f"— {str(o.get('category','')).title()} "
                            f"&nbsp; {badge}",
                            unsafe_allow_html=True
                        )

st.markdown("<br><hr>", unsafe_allow_html=True)
st.caption("AMK Fashion Hub · Anjali Ladies Boutique · Muggam, Kerala · 9876543210")
