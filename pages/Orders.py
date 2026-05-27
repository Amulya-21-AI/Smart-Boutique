"""
Smart-Boutique/pages/Orders.py
"""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import streamlit as st
import datetime
import uuid
from database.db import init_db, run_query, run_update

st.set_page_config(page_title="Orders · Smart Boutique", page_icon="📦", layout="wide")
init_db()

from utils.auth import require_auth
role, cust_id = require_auth()   # both admin and customer

GOLD = "#c9a96e"

# ── Status colour helper ──────────────────────────────────────────────────────
def status_color(val):
    colors = {
        "Delivered": "background-color:#0d3b2e; color:#2ecc71",
        "Cancelled": "background-color:#3b0d0d; color:#e74c3c",
        "Returned":  "background-color:#3b2a0d; color:#f39c12",
        "Shipped":   "background-color:#0d2a3b; color:#3498db",
        "Pending":   "background-color:#1a1a3b; color:#9b59b6",
    }
    return colors.get(val, "")


# ══════════════════════════════════════════════════════════════════════════════
# ADMIN VIEW — full order management
# ══════════════════════════════════════════════════════════════════════════════
if role == 'admin':
    st.markdown(f"<h1 style='color:{GOLD}'>📦 Order Management</h1>", unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs([
        "📋 All Orders", "🔍 Order Lookup", "✏️ Update Status", "➕ New Order"
    ])

    # ── TAB 1: ALL ORDERS ─────────────────────────────────────────────────────
    with tab1:
        st.subheader("Order History")

        fc1, fc2, fc3, fc4 = st.columns(4)
        with fc1:
            statuses   = run_query("SELECT DISTINCT status FROM orders WHERE status IS NOT NULL")["status"].tolist()
            sel_status = st.multiselect("Status", statuses, default=statuses)
        with fc2:
            cats    = run_query("SELECT DISTINCT category FROM orders WHERE category IS NOT NULL ORDER BY category")["category"].tolist()
            sel_cat = st.multiselect("Category", cats, default=cats)
        with fc3:
            sel_season = st.multiselect("Season", ["Spring","Summer","Autumn","Winter"],
                                        default=["Spring","Summer","Autumn","Winter"])
        with fc4:
            b2b_opt = st.radio("Type", ["All","B2B","B2C"], horizontal=True)

        _statuses = sel_status if sel_status else statuses
        _cats     = sel_cat    if sel_cat    else cats
        _seasons  = sel_season if sel_season else ["Spring","Summer","Autumn","Winter"]
        status_in = ",".join([f"'{s}'" for s in _statuses])
        cat_in    = ",".join([f"'{c}'" for c in _cats])
        sea_in    = ",".join([f"'{s}'" for s in _seasons])
        b2b_sql   = {"B2B":"AND b2b=1","B2C":"AND b2b=0"}.get(b2b_opt,"")

        df = run_query(f"""
            SELECT o.order_id, o.cust_id, c.name AS customer,
                   o.category, o.size, o.qty, o.amount, o.status,
                   o.season, o.weekend_order, o.return_flag,
                   o.order_date, o.ship_state, o.retail_supplier, o.b2b
            FROM orders o
            LEFT JOIN customers c ON o.cust_id = c.cust_id
            WHERE o.status IN ({status_in})
            AND o.category IN ({cat_in})
            AND (o.season IN ({sea_in}) OR o.season IS NULL)
            {b2b_sql}
            ORDER BY o.order_date DESC
            LIMIT 5000
        """)

        if df.empty:
            st.info("No orders match your filters.")
        else:
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Filtered Orders", f"{len(df):,}")
            k2.metric("Revenue (₹)",     f"{df['amount'].sum():,.0f}")
            k3.metric("Returns",         int(df['return_flag'].sum()))
            k4.metric("Weekend Orders",  int(df['weekend_order'].sum()))

            styled = df.style.applymap(status_color, subset=["status"])
            st.dataframe(styled, use_container_width=True, height=450)

            csv = df.to_csv(index=False).encode()
            st.download_button("⬇️ Export Filtered Orders", csv,
                               "orders_filtered.csv", "text/csv")

    # ── TAB 2: ORDER LOOKUP ───────────────────────────────────────────────────
    with tab2:
        st.subheader("Look Up a Specific Order")
        search_oid = st.text_input("Enter Order ID")
        if st.button("🔍 Find Order") and search_oid:
            res = run_query(f"""
                SELECT o.*, c.name AS customer_name, c.phone, c.email
                FROM orders o
                LEFT JOIN customers c ON o.cust_id = c.cust_id
                WHERE o.order_id = '{search_oid.strip()}'
            """)
            if res.empty:
                st.warning("Order not found.")
            else:
                row = res.iloc[0]
                st.markdown(f"### Order: `{row['order_id']}`")
                c1, c2, c3 = st.columns(3)
                c1.markdown(f"**Customer:** {row.get('customer_name','—')}  \n"
                            f"**Cust ID:** {row['cust_id']}")
                c2.markdown(f"**Category:** {row['category']}  \n"
                            f"**Size:** {row['size']} | Qty: {row['qty']}")
                c3.markdown(f"**Amount:** ₹{float(row['amount']):,.0f}  \n"
                            f"**Status:** {row['status']}")
                st.markdown(f"**Order Date:** {row['order_date']}  |  "
                            f"**Season:** {row.get('season','—')}  |  "
                            f"**Supplier:** {row.get('retail_supplier','—')}")

    # ── TAB 3: UPDATE STATUS ──────────────────────────────────────────────────
    with tab3:
        st.subheader("Update Order Status")
        st.info("Fill actual delivery days here — this trains the ML delivery prediction model.")
        with st.form("update_form"):
            upd_id     = st.text_input("Order ID to update")
            new_status = st.selectbox("New Status",
                                      ["Delivered","Shipped","Returned","Cancelled","Pending"])
            del_days   = st.number_input("Actual Delivery Days",
                                         min_value=0, max_value=180, value=0)
            upd_submit = st.form_submit_button("✅ Update Order")

        if upd_submit and upd_id:
            return_flag = 1 if new_status in ("Returned","Cancelled") else 0
            rows = run_update("""
                UPDATE orders SET status=?, return_flag=?, delivery_days=?
                WHERE order_id=?
            """, (new_status, return_flag,
                  int(del_days) if del_days else None,
                  upd_id.strip()))
            if rows:
                st.success(f"✅ Order `{upd_id}` updated to **{new_status}**.")
            else:
                st.error("Order ID not found.")

        st.divider()
        st.subheader("Assign Tailor to Order")
        tailors_df = run_query(
            "SELECT tailor_id, name, specialty, availability FROM tailors ORDER BY name"
        )
        if tailors_df.empty:
            st.info("No tailors registered yet. Add tailors in the Tailors page.")
        else:
            with st.form("assign_tailor_form"):
                assign_oid = st.text_input("Order ID")
                avail = tailors_df[tailors_df['availability'] == 'Available']
                if avail.empty:
                    st.warning("No available tailors right now.")
                    assign_submit = st.form_submit_button("Assign", disabled=True)
                else:
                    options = {f"{r['name']} ({r['specialty']})": r['tailor_id']
                               for _, r in avail.iterrows()}
                    sel_tailor = st.selectbox("Select Available Tailor", list(options.keys()))
                    assign_submit = st.form_submit_button("✅ Assign Tailor")

            if assign_submit and assign_oid and not avail.empty:
                tid = options[sel_tailor]
                rows = run_update("UPDATE orders SET tailor_id=? WHERE order_id=?",
                                  (tid, assign_oid.strip()))
                if rows:
                    st.success(f"Tailor **{sel_tailor}** assigned to order `{assign_oid}`.")
                else:
                    st.error("Order ID not found.")

    # ── TAB 4: NEW ORDER ──────────────────────────────────────────────────────
    with tab4:
        st.markdown(f"<h3 style='color:{GOLD}'>➕ Place a New Order</h3>",
                    unsafe_allow_html=True)
        st.markdown("Fill in all the details below and click **Submit Order** at the bottom.")
        st.divider()

        st.markdown("#### 👤 Customer Information")
        nc1, nc2 = st.columns(2)
        with nc1:
            no_cust_id = st.text_input("Customer ID *", placeholder="e.g. 1029312")
            if no_cust_id.strip():
                cust_check = run_query(
                    "SELECT cust_id, name, phone, address, city, state FROM customers "
                    "WHERE CAST(cust_id AS TEXT) = ?", (no_cust_id.strip(),)
                )
                if not cust_check.empty:
                    cr = cust_check.iloc[0]
                    st.success(f"✅ Found: **{cr['name']}**")
                    _an, _ap, _aa, _ac, _as = (
                        cr['name'], str(cr.get('phone','')),
                        str(cr.get('address','')), str(cr.get('city','')),
                        str(cr.get('state',''))
                    )
                else:
                    st.error("❌ Customer ID not found.")
                    _an = _ap = _aa = _ac = _as = ""
            else:
                _an = _ap = _aa = _ac = _as = ""
        with nc2:
            no_order_date = st.date_input("Order Date *", value=datetime.date.today())

        nc3, nc4 = st.columns(2)
        with nc3:
            no_cust_name = st.text_input("Customer Name *", value=_an)
        with nc4:
            no_phone = st.text_input("Phone *", value=_ap)

        no_address = st.text_area("Delivery Address *", value=_aa, height=70)
        nc5, nc6 = st.columns(2)
        with nc5:
            no_city  = st.text_input("City *", value=_ac)
        with nc6:
            no_state = st.text_input("State *", value=_as if _as else "KERALA")

        st.divider()
        st.markdown("#### 🥻 Product Details")
        pp1, pp2, pp3 = st.columns(3)
        with pp1:
            no_category = st.selectbox("Category *",
                ["kurta","set","western dress","top","saree","blouse","ethnic dress","bottom"],
                key="adm_cat")
        with pp2:
            no_size = st.selectbox("Size *",
                ["XS","S","M","L","XL","XXL","3XL","Free"], key="adm_size")
        with pp3:
            no_qty = st.number_input("Quantity *", min_value=1, max_value=50, value=1,
                                      key="adm_qty")

        pp4, pp5 = st.columns(2)
        with pp4:
            no_design = st.text_area("Design Description *",
                placeholder="Describe the design in detail…", height=120, key="adm_des")
        with pp5:
            no_model = st.text_area("Model / Style Reference",
                placeholder="e.g. Anarkali, Straight Cut…", height=120, key="adm_mod")

        st.divider()
        st.markdown("#### 💰 Pricing & Order Info")
        oo1, oo2, oo3 = st.columns(3)
        with oo1:
            no_amount = st.number_input("Total Amount (₹) *",
                min_value=0, max_value=100000, value=500, step=50, key="adm_amt")
        with oo2:
            no_supplier = st.selectbox("Retail Supplier",
                ["Myntra","Ajio","Amazon","Flipkart","Meesho","Nalli","Other"],
                key="adm_sup")
        with oo3:
            no_season = st.selectbox("Season",
                ["Spring","Summer","Autumn","Winter"], key="adm_sea")

        oo4, oo5 = st.columns(2)
        with oo4:
            no_b2b = st.radio("Order Type", ["B2C","B2B"], horizontal=True, key="adm_b2b")
        with oo5:
            no_sku = st.text_input("SKU / Product Code", key="adm_sku")

        st.divider()
        adm_submit = st.button("✅ Submit Order", use_container_width=True,
                                type="primary", key="adm_submit")

        if adm_submit:
            adm_errors = []
            if not no_cust_id.strip():   adm_errors.append("Customer ID is required.")
            if not no_cust_name.strip(): adm_errors.append("Customer Name is required.")
            if not no_phone.strip() or not no_phone.strip().isdigit() or len(no_phone.strip()) != 10:
                adm_errors.append("Phone must be 10 digits.")
            if not no_address.strip():   adm_errors.append("Address is required.")
            if not no_city.strip():      adm_errors.append("City is required.")
            if not no_design.strip():    adm_errors.append("Design description is required.")
            if no_amount <= 0:           adm_errors.append("Amount must be > 0.")

            if adm_errors:
                for e in adm_errors: st.error(e)
            else:
                cv = run_query(
                    "SELECT cust_id FROM customers WHERE CAST(cust_id AS TEXT)=?",
                    (no_cust_id.strip(),)
                )
                if cv.empty:
                    st.error("Customer ID not found.")
                else:
                    wknd     = 1 if no_order_date.weekday() >= 5 else 0
                    order_id = f"ORD-{uuid.uuid4().hex[:10].upper()}"
                    run_update("""
                        INSERT INTO orders (
                            order_id, cust_id, category, size, qty, amount,
                            gender, b2b, retail_supplier, ship_state, ship_city,
                            season, weekend_order, return_flag, status, order_date, sku
                        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """, (
                        order_id, int(no_cust_id.strip()), no_category, no_size,
                        int(no_qty), float(no_amount), 'W',
                        1 if no_b2b == "B2B" else 0, no_supplier,
                        no_state.strip().upper(), no_city.strip(), no_season,
                        wknd, 0, "Pending", str(no_order_date),
                        no_sku.strip() or None
                    ))
                    st.success(f"🎉 Order `{order_id}` placed for **{no_cust_name}**.")
                    st.balloons()

# ══════════════════════════════════════════════════════════════════════════════
# CUSTOMER VIEW — own orders + place new order
# ══════════════════════════════════════════════════════════════════════════════
else:
    st.markdown(f"<h1 style='color:{GOLD}'>📦 My Orders</h1>", unsafe_allow_html=True)

    col_ai, col_rec = st.columns(2)
    with col_ai:
        st.info("✨ **Need design help?** Ask our AI Style Advisor before placing an order.")
        if st.button("Open AI Style Advisor", use_container_width=True):
            st.switch_page("pages/GenAI_RAG_Assistant.py")
    with col_rec:
        st.info("🎯 **Want recommendations?** Get personalised style picks from our ML model.")
        if st.button("View Style Recommendations", use_container_width=True):
            st.switch_page("pages/ML_Recommendation.py")

    st.markdown("<br>", unsafe_allow_html=True)

    cust_tab1, cust_tab2, cust_tab3 = st.tabs(["📋 My Orders", "🔍 Track Order", "➕ Place New Order"])

    # ── MY ORDERS ─────────────────────────────────────────────────────────────
    with cust_tab1:
        my_orders = run_query("""
            SELECT o.order_id, o.order_date, o.category, o.size, o.qty,
                   o.amount, o.status, o.return_flag,
                   o.delivery_date, o.estimated_days, o.delivery_days,
                   o.ship_city, o.ship_state, o.b2b, o.retail_supplier,
                   t.name AS tailor_name
            FROM orders o
            LEFT JOIN tailors t ON o.tailor_id = t.tailor_id
            WHERE o.cust_id = ?
            ORDER BY o.order_date DESC
        """, (cust_id,))

        if my_orders.empty:
            st.info("You have no orders yet. Use **Place New Order** tab to get started.")
        else:
            k1, k2, k3 = st.columns(3)
            k1.metric("Total Orders",  f"{len(my_orders):,}")
            k2.metric("Total Spent",   f"₹{my_orders['amount'].sum():,.0f}")
            k3.metric("Active Orders", int(my_orders['status'].isin(['Pending','Shipped']).sum()))

            styled = my_orders.style.applymap(status_color, subset=["status"])
            st.dataframe(styled, use_container_width=True, height=400,
                         column_config={
                             "order_id":   st.column_config.TextColumn("Order ID"),
                             "amount":     st.column_config.NumberColumn("Amount (₹)", format="₹%.0f"),
                             "status":     st.column_config.TextColumn("Status"),
                             "order_date": st.column_config.TextColumn("Date"),
                             "tailor_name":st.column_config.TextColumn("Tailor"),
                         })

    # ── TRACK ORDER ───────────────────────────────────────────────────────────
    with cust_tab2:
        st.subheader("Track a Specific Order")
        track_id = st.text_input("Enter your Order ID", placeholder="e.g. ORD-ABC123")
        if st.button("🔍 Track") and track_id.strip():
            res = run_query("""
                SELECT o.order_id, o.order_date, o.category, o.size, o.qty,
                       o.amount, o.status, o.return_flag,
                       o.delivery_date, o.estimated_days, o.delivery_days,
                       o.ship_city, o.ship_state, o.b2b, o.retail_supplier,
                       t.name AS tailor_name, t.phone AS tailor_phone
                FROM orders o
                LEFT JOIN tailors t ON o.tailor_id = t.tailor_id
                WHERE o.order_id = ? AND o.cust_id = ?
            """, (track_id.strip(), cust_id))

            if res.empty:
                st.warning("Order not found or it doesn't belong to your account.")
            else:
                row = res.iloc[0]
                status = row.get('status', 'Pending')
                is_pickup = (not row.get('b2b') and
                             not str(row.get('ship_city', '')).strip())
                est = row.get('estimated_days') or row.get('delivery_days')

                PROGRESS = {
                    "Pending":   ("In Queue",           20,  "#9b59b6"),
                    "Shipped":   ("Work in Progress",   60,  "#3498db"),
                    "Delivered": ("Ready / Completed", 100,  "#2ecc71"),
                    "Cancelled": ("Cancelled",            0, "#e74c3c"),
                    "Returned":  ("Returned",             0, "#f39c12"),
                }
                label, pct, bar_color = PROGRESS.get(status, ("Unknown", 0, "#aaa"))

                st.markdown(f"### Order `{row['order_id']}`")
                d1, d2, d3 = st.columns(3)
                d1.markdown(f"**Category:** {row['category']}  \n"
                            f"**Size:** {row['size']} | Qty: {row['qty']}")
                d2.markdown(f"**Amount:** ₹{float(row['amount']):,.0f}  \n"
                            f"**Order Date:** {row['order_date']}")
                d3.markdown(f"**Status:** {status}  \n"
                            f"**Tailor:** {row.get('tailor_name','Not assigned yet')}")

                st.markdown(f"""
<div style='margin:1rem 0;'>
  <div style='display:flex;justify-content:space-between;
              font-size:0.85rem;color:#aaa;margin-bottom:6px;'>
    <span>Work Progress</span><span>{label}</span>
  </div>
  <div style='background:#ffffff15;border-radius:999px;height:10px;overflow:hidden;'>
    <div style='width:{pct}%;background:{bar_color};height:100%;
                border-radius:999px;'></div>
  </div>
</div>
""", unsafe_allow_html=True)

                if is_pickup and status not in ("Delivered", "Cancelled"):
                    st.info(
                        f"🏠 **Pickup Order** — Please visit the boutique in approx. "
                        f"**{est or '7–10'} days** from your order date to collect your outfit.  \n"
                        f"📞 Boutique: **9876543210** · Muggam, Kerala"
                    )
                elif est and not is_pickup and status not in ("Delivered", "Cancelled"):
                    st.info(f"🚚 Estimated delivery: **{est} days** from order date.")

                if row.get('tailor_phone'):
                    st.success(
                        f"✂️ Your tailor **{row['tailor_name']}** can be reached at "
                        f"**{row['tailor_phone']}** for updates."
                    )

    # ── PLACE NEW ORDER ───────────────────────────────────────────────────────
    with cust_tab3:
        st.markdown(f"<h3 style='color:{GOLD}'>➕ Place a New Order</h3>",
                    unsafe_allow_html=True)

        # Look up customer info to pre-fill
        cust_info = run_query(
            "SELECT name, phone, address, city, state FROM customers WHERE cust_id=?",
            (cust_id,)
        )
        _auto = cust_info.iloc[0].to_dict() if not cust_info.empty else {}

        st.markdown(f"**Your Customer ID:** `CUST-{cust_id}`", )
        st.divider()

        st.markdown("#### 🥻 Product Details")
        p1, p2, p3 = st.columns(3)
        with p1:
            no_category = st.selectbox("Category *",
                ["kurta","set","western dress","top","saree","blouse","ethnic dress","bottom"])
        with p2:
            no_size = st.selectbox("Size *",
                ["XS","S","M","L","XL","XXL","3XL","Free"])
        with p3:
            no_qty = st.number_input("Quantity *", min_value=1, max_value=50, value=1)

        p4, p5 = st.columns(2)
        with p4:
            no_design = st.text_area("Design Description *",
                placeholder="Describe your design: colours, embroidery, neckline style, "
                            "sleeve type, length, any special requests…", height=120)
        with p5:
            no_model = st.text_area("Model / Style Reference",
                placeholder="Reference model or style number.  "
                            "e.g. Anarkali, Straight Cut, Palazzo Set 2024…", height=120)

        st.markdown("#### 📦 Delivery Details")
        d1, d2 = st.columns(2)
        with d1:
            no_order_date = st.date_input("Order Date *", value=datetime.date.today())
            no_amount = st.number_input("Total Amount (₹) *",
                                         min_value=0, max_value=100000, value=500, step=50)
        with d2:
            delivery_type = st.radio("Delivery Type",
                ["🏠 Pickup from boutique", "🚚 Home delivery"], horizontal=True)
            no_season = st.selectbox("Season",
                ["Spring","Summer","Autumn","Winter"])

        if "Home delivery" in delivery_type:
            no_address = st.text_area("Delivery Address *",
                value=_auto.get('address',''), height=70)
            dc1, dc2 = st.columns(2)
            with dc1:
                no_city = st.text_input("City *", value=_auto.get('city',''))
            with dc2:
                no_state = st.text_input("State *",
                    value=_auto.get('state','KERALA') or 'KERALA')
        else:
            no_address = "Boutique Pickup"
            no_city    = "Muggam"
            no_state   = "KERALA"
            st.info("🏠 You will be notified when your outfit is ready for pickup.  \n"
                    "📞 Boutique: **9876543210**")

        st.divider()
        submit_btn = st.button("✅ Submit Order", use_container_width=True, type="primary")

        if submit_btn:
            errors = []
            if not no_design.strip():
                errors.append("Design description is required.")
            if no_amount <= 0:
                errors.append("Order amount must be greater than 0.")
            if "Home delivery" in delivery_type:
                if not no_city.strip():  errors.append("City is required.")
                if not no_state.strip(): errors.append("State is required.")

            if errors:
                for e in errors: st.error(e)
            else:
                weekend_order = 1 if no_order_date.weekday() >= 5 else 0
                order_id      = f"ORD-{uuid.uuid4().hex[:10].upper()}"
                is_pickup     = "Pickup" in delivery_type

                design_notes = f"Design: {no_design.strip()}"
                if no_model.strip():
                    design_notes += f" | Model: {no_model.strip()}"

                rows = run_update("""
                    INSERT INTO orders (
                        order_id, cust_id, category, size, qty,
                        amount, gender, b2b, ship_state, ship_city,
                        season, weekend_order, return_flag, status,
                        order_date, sku
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    order_id, int(cust_id), no_category, no_size, int(no_qty),
                    float(no_amount), 'W', 0,
                    no_state.strip().upper(), no_city.strip() if not is_pickup else '',
                    no_season, weekend_order, 0, "Pending",
                    str(no_order_date), None
                ))

                if rows is not None:
                    st.success("🎉 Order placed successfully!")
                    st.balloons()
                    st.markdown(f"""
<div style='background:linear-gradient(135deg,#1a0a2e,#16213e);
            border:1px solid #c9a96e44;border-radius:14px;padding:1.5rem;margin-top:1rem;'>
  <div style='font-size:1.1rem;font-weight:600;color:#c9a96e;margin-bottom:1rem;'>
    📋 Order Confirmation</div>
  <table style='width:100%;border-collapse:collapse;font-size:0.9rem;'>
    <tr>
      <td style='color:#aaa;padding:4px 0;width:35%;'>Order ID</td>
      <td style='color:#f5e6d3;font-weight:500;'>
        <code style='background:#ffffff11;padding:2px 8px;border-radius:4px;
                     color:#c9a96e;'>{order_id}</code></td>
    </tr>
    <tr>
      <td style='color:#aaa;padding:4px 0;'>Customer ID</td>
      <td style='color:#f5e6d3;'>CUST-{cust_id}</td>
    </tr>
    <tr>
      <td style='color:#aaa;padding:4px 0;'>Product</td>
      <td style='color:#f5e6d3;'>{no_category.title()} · Size {no_size} · Qty {int(no_qty)}</td>
    </tr>
    <tr>
      <td style='color:#aaa;padding:4px 0;'>Design</td>
      <td style='color:#f5e6d3;'>
        {no_design.strip()[:80]}{"..." if len(no_design) > 80 else ""}</td>
    </tr>
    <tr>
      <td style='color:#aaa;padding:4px 0;'>Amount</td>
      <td style='color:#c9a96e;font-weight:600;font-size:1.1rem;'>
        ₹{float(no_amount):,.0f}</td>
    </tr>
    <tr>
      <td style='color:#aaa;padding:4px 0;'>Delivery</td>
      <td style='color:#f5e6d3;'>
        {"🏠 Pickup from boutique" if is_pickup else f"🚚 {no_city}, {no_state}"}</td>
    </tr>
    <tr>
      <td style='color:#aaa;padding:4px 0;'>Status</td>
      <td style='color:#9b59b6;font-weight:500;'>⏳ Pending</td>
    </tr>
  </table>
</div>
""", unsafe_allow_html=True)
                    st.info("Track your order using the **Track Order** tab above.")
                else:
                    st.error("Failed to place order. Please try again.")


st.markdown("<br><hr>", unsafe_allow_html=True)
st.caption("AMK Fashion Hub · Anjali Ladies Boutique · Muggam, Kerala")
