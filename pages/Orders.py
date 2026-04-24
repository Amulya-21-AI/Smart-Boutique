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
</style>
""", unsafe_allow_html=True)

st.markdown(f"<h1 style='color:{GOLD}'>📦 Order Management</h1>", unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs([
    "📋 All Orders",
    "🔍 Order Lookup",
    "✏️ Update Status",
    "➕ New Order"
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — ALL ORDERS
# ══════════════════════════════════════════════════════════════════════════════
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

    # FIX: if filter is empty, fall back to full list so table never goes blank
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

        def status_color(val):
            colors = {
                "Delivered": "background-color:#0d3b2e; color:#2ecc71",
                "Cancelled": "background-color:#3b0d0d; color:#e74c3c",
                "Returned":  "background-color:#3b2a0d; color:#f39c12",
                "Shipped":   "background-color:#0d2a3b; color:#3498db",
                "Pending":   "background-color:#1a1a3b; color:#9b59b6",
            }
            return colors.get(val, "")

        styled = df.style.applymap(status_color, subset=["status"])
        st.dataframe(styled, use_container_width=True, height=450)

        csv = df.to_csv(index=False).encode()
        st.download_button("⬇️ Export Filtered Orders", csv,
                           "orders_filtered.csv", "text/csv")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — ORDER LOOKUP
# ══════════════════════════════════════════════════════════════════════════════
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

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — UPDATE STATUS
# ══════════════════════════════════════════════════════════════════════════════
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

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — NEW ORDER
# ══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.markdown(f"<h3 style='color:{GOLD}'>➕ Place a New Order</h3>",
                unsafe_allow_html=True)
    st.markdown("Fill in all the details below and click **Submit Order** at the bottom.")
    st.divider()

    # ── SECTION 1: Customer Info ──────────────────────────────────────────────
    st.markdown(f"#### 👤 Customer Information")

    c1, c2 = st.columns(2)
    with c1:
        no_cust_id = st.text_input(
            "Customer ID *",
            placeholder="e.g. 1029312",
            help="Enter the Customer ID from the Customers page."
        )
        # Live customer lookup as they type
        if no_cust_id.strip():
            cust_check = run_query(f"""
                SELECT cust_id, name, phone, age, gender, city, state, address
                FROM customers
                WHERE CAST(cust_id AS TEXT) = '{no_cust_id.strip()}'
            """)
            if not cust_check.empty:
                cr = cust_check.iloc[0]
                st.success(f"✅ Found: **{cr['name']}**")
                # Pre-fill display values
                _auto_name    = cr['name']
                _auto_phone   = str(cr.get('phone', ''))
                _auto_address = str(cr.get('address', ''))
                _auto_city    = str(cr.get('city', ''))
                _auto_state   = str(cr.get('state', ''))
            else:
                st.error("❌ Customer ID not found. Register in Customers page first.")
                _auto_name    = ""
                _auto_phone   = ""
                _auto_address = ""
                _auto_city    = ""
                _auto_state   = ""
        else:
            _auto_name    = ""
            _auto_phone   = ""
            _auto_address = ""
            _auto_city    = ""
            _auto_state   = ""

    with c2:
        no_order_date = st.date_input(
            "Order Date *",
            value=datetime.date.today()
        )

    c3, c4 = st.columns(2)
    with c3:
        no_cust_name = st.text_input(
            "Customer Name *",
            value=_auto_name,
            placeholder="Auto-filled from Customer ID"
        )
    with c4:
        no_phone = st.text_input(
            "Phone Number *",
            value=_auto_phone,
            placeholder="10-digit mobile number"
        )

    no_address = st.text_area(
        "Delivery Address *",
        value=_auto_address,
        placeholder="House / Street / Landmark",
        height=80
    )

    c5, c6 = st.columns(2)
    with c5:
        no_city = st.text_input(
            "City *",
            value=_auto_city,
            placeholder="e.g. Muggam"
        )
    with c6:
        no_state = st.text_input(
            "State *",
            value=_auto_state if _auto_state else "KERALA",
            placeholder="e.g. KERALA"
        )

    st.divider()

    # ── SECTION 2: Product Details ────────────────────────────────────────────
    st.markdown(f"#### 🥻 Product Details")

    p1, p2, p3 = st.columns(3)
    with p1:
        no_category = st.selectbox(
            "Category *",
            ["kurta", "set", "western dress", "top",
             "saree", "blouse", "ethnic dress", "bottom"]
        )
    with p2:
        no_size = st.selectbox(
            "Size *",
            ["XS", "S", "M", "L", "XL", "XXL", "3XL", "Free"]
        )
    with p3:
        no_qty = st.number_input(
            "Quantity *",
            min_value=1, max_value=50, value=1
        )

    p4, p5 = st.columns(2)
    with p4:
        no_design = st.text_area(
            "Design Description *",
            placeholder=(
                "Describe the design in detail.\n"
                "e.g. Floral embroidery on neckline, mirror work on sleeves, "
                "A-line kurta with side slits, deep red colour with golden border..."
            ),
            height=120
        )
    with p5:
        no_model = st.text_area(
            "Model / Style Reference",
            placeholder=(
                "Reference model or style number.\n"
                "e.g. Anarkali Model, Straight Cut Model, "
                "Palazzo Set Style 2024, Customer's own reference image description..."
            ),
            height=120
        )

    st.divider()

    # ── SECTION 3: Pricing & Order Info ───────────────────────────────────────
    st.markdown(f"#### 💰 Pricing & Order Info")

    o1, o2, o3 = st.columns(3)
    with o1:
        no_amount = st.number_input(
            "Total Amount (₹) *",
            min_value=0, max_value=100000, value=500,
            step=50
        )
    with o2:
        no_supplier = st.selectbox(
            "Retail Supplier",
            ["Myntra", "Ajio", "Amazon", "Flipkart",
             "Meesho", "Nalli", "Other"]
        )
    with o3:
        no_season = st.selectbox(
            "Season",
            ["Spring", "Summer", "Autumn", "Winter"]
        )

    o4, o5, o6 = st.columns(3)
    with o4:
        no_b2b = st.radio("Order Type", ["B2C", "B2B"], horizontal=True)
    with o5:
        no_sku = st.text_input(
            "SKU / Product Code",
            placeholder="e.g. KRT-M-001 (optional)"
        )
    with o6:
        st.markdown("<br>", unsafe_allow_html=True)
        st.caption("All orders registered for women's boutique")

    st.divider()

    # ── SUBMIT BUTTON ─────────────────────────────────────────────────────────
    col_submit, col_clear = st.columns([3, 1])
    with col_submit:
        submit_btn = st.button(
            "✅ Submit Order",
            use_container_width=True,
            type="primary"
        )
    with col_clear:
        st.button("🗑️ Clear Form", use_container_width=True)

    # ── VALIDATION & INSERT ───────────────────────────────────────────────────
    if submit_btn:
        errors = []

        if not no_cust_id.strip():
            errors.append("Customer ID is required.")
        if not no_cust_name.strip():
            errors.append("Customer Name is required.")
        if not no_phone.strip():
            errors.append("Phone Number is required.")
        elif not no_phone.strip().isdigit() or len(no_phone.strip()) != 10:
            errors.append("Phone must be exactly 10 digits.")
        if not no_address.strip():
            errors.append("Delivery Address is required.")
        if not no_city.strip():
            errors.append("City is required.")
        if not no_state.strip():
            errors.append("State is required.")
        if not no_design.strip():
            errors.append("Design Description is required.")
        if no_amount <= 0:
            errors.append("Order amount must be greater than 0.")

        if errors:
            st.error("Please fix the following before submitting:")
            for e in errors:
                st.markdown(f"- {e}")
        else:
            # Verify customer exists
            cust_verify = run_query(f"""
                SELECT cust_id, name FROM customers
                WHERE CAST(cust_id AS TEXT) = '{no_cust_id.strip()}'
            """)

            if cust_verify.empty:
                st.error(
                    f"❌ Customer ID **{no_cust_id}** not found in the database. "
                    "Please register this customer in the **Customers** page first."
                )
            else:
                # Build all derived values
                weekend_order = 1 if no_order_date.weekday() >= 5 else 0
                order_id      = f"ORD-{uuid.uuid4().hex[:10].upper()}"
                b2b_val       = 1 if no_b2b == "B2B" else 0
                state_upper   = no_state.strip().upper()
                no_sku_val    = no_sku.strip() if no_sku.strip() else None

                # Combine design + model into notes field
                design_notes = f"Design: {no_design.strip()}"
                if no_model.strip():
                    design_notes += f" | Model: {no_model.strip()}"

                # Insert into orders table
                rows = run_update("""
                    INSERT INTO orders (
                        order_id, cust_id, category, size, qty,
                        amount, gender, b2b, retail_supplier,
                        ship_state, ship_city, season,
                        weekend_order, return_flag, status,
                        order_date, sku
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    order_id,
                    int(no_cust_id.strip()),
                    no_category,
                    no_size,
                    int(no_qty),
                    float(no_amount),
                    'W',
                    b2b_val,
                    no_supplier,
                    state_upper,
                    no_city.strip(),
                    no_season,
                    weekend_order,
                    0,
                    "Pending",
                    str(no_order_date),
                    no_sku_val
                ))

                if rows is not None:
                    st.success("🎉 Order placed successfully!")
                    st.balloons()

                    # ── Order summary card ────────────────────────────────────
                    st.markdown(f"""
<div style='background:linear-gradient(135deg,#1a0a2e,#16213e);
            border:1px solid #c9a96e44; border-radius:14px;
            padding:1.5rem; margin-top:1rem;'>
  <div style='font-size:1.1rem; font-weight:600; color:#c9a96e;
              margin-bottom:1rem;'>📋 Order Confirmation</div>
  <table style='width:100%; border-collapse:collapse; font-size:0.9rem;'>
    <tr>
      <td style='color:#aaa; padding:4px 0; width:35%;'>Order ID</td>
      <td style='color:#f5e6d3; font-weight:500;'><code style='background:#ffffff11;
          padding:2px 8px; border-radius:4px;'>{order_id}</code></td>
    </tr>
    <tr>
      <td style='color:#aaa; padding:4px 0;'>Customer</td>
      <td style='color:#f5e6d3;'>{no_cust_name} &nbsp;|&nbsp; {no_phone}</td>
    </tr>
    <tr>
      <td style='color:#aaa; padding:4px 0;'>Product</td>
      <td style='color:#f5e6d3;'>{no_category.title()} · Size {no_size} · Qty {int(no_qty)}</td>
    </tr>
    <tr>
      <td style='color:#aaa; padding:4px 0;'>Design</td>
      <td style='color:#f5e6d3;'>{no_design.strip()[:80]}{'...' if len(no_design)>80 else ''}</td>
    </tr>
    <tr>
      <td style='color:#aaa; padding:4px 0;'>Amount</td>
      <td style='color:#c9a96e; font-weight:600; font-size:1.1rem;'>₹{float(no_amount):,.0f}</td>
    </tr>
    <tr>
      <td style='color:#aaa; padding:4px 0;'>Deliver To</td>
      <td style='color:#f5e6d3;'>{no_address.strip()[:60]}, {no_city}, {state_upper}</td>
    </tr>
    <tr>
      <td style='color:#aaa; padding:4px 0;'>Order Date</td>
      <td style='color:#f5e6d3;'>{no_order_date.strftime('%d %b %Y')}</td>
    </tr>
    <tr>
      <td style='color:#aaa; padding:4px 0;'>Status</td>
      <td style='color:#9b59b6; font-weight:500;'>⏳ Pending</td>
    </tr>
  </table>
</div>
""", unsafe_allow_html=True)

                    st.info(
                        "✅ This order now appears in **All Orders** tab and "
                        "updates the **Dashboard** automatically. "
                        "Go to **Update Status** tab to mark it as Shipped or Delivered."
                    )
                else:
                    st.error("❌ Failed to place order. Please try again.")
