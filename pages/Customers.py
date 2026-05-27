"""
Smart-Boutique/pages/Customers.py
"""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import streamlit as st
from database.db import (init_db, insert_customer, get_all_customers,
                          check_duplicate_customer, run_query)

st.set_page_config(page_title="Customers · Smart Boutique", page_icon="👥", layout="wide")
init_db()

from utils.auth import require_auth
role, cust_id = require_auth(['admin'])

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

st.markdown(f"<h1 style='color:{GOLD}'>👥 Customer Management</h1>", unsafe_allow_html=True)

# ── IMPROVEMENT 3: Kerala pincode → city/state lookup ─────────────────────────
KERALA_PINCODES = {
    # Kozhikode district
    "673001": ("Kozhikode", "KERALA"),
    "673002": ("Kozhikode", "KERALA"),
    "673003": ("Kozhikode", "KERALA"),
    "673004": ("Kozhikode", "KERALA"),
    "673005": ("Kozhikode", "KERALA"),
    "673006": ("Kozhikode", "KERALA"),
    "673007": ("Kozhikode", "KERALA"),
    "673008": ("Kozhikode", "KERALA"),
    "673009": ("Kozhikode", "KERALA"),
    "673010": ("Kozhikode", "KERALA"),
    "673011": ("Kozhikode", "KERALA"),
    "673012": ("Kozhikode", "KERALA"),
    "673014": ("Kozhikode", "KERALA"),
    "673016": ("Kozhikode", "KERALA"),
    "673017": ("Kozhikode", "KERALA"),
    "673019": ("Kozhikode", "KERALA"),
    "673020": ("Kozhikode", "KERALA"),
    "673021": ("Kozhikode", "KERALA"),
    "673028": ("Kozhikode", "KERALA"),
    "673029": ("Kozhikode", "KERALA"),
    "673032": ("Kozhikode", "KERALA"),
    "673101": ("Vatakara", "KERALA"),
    "673102": ("Vadakara", "KERALA"),
    "673104": ("Feroke", "KERALA"),
    "673105": ("Mukkam", "KERALA"),
    "673106": ("Muggam", "KERALA"),   # ← Anjali Boutique location
    "673107": ("Perambra", "KERALA"),
    "673108": ("Thiruvambady", "KERALA"),
    "673109": ("Quilandy", "KERALA"),
    "673110": ("Koyilandy", "KERALA"),
    "673111": ("Thalassery", "KERALA"),
    "673112": ("Ramanattukara", "KERALA"),
    "673121": ("Kalpetta", "KERALA"),
    "673122": ("Mananthavady", "KERALA"),
    "673123": ("Sultan Bathery", "KERALA"),
    "673124": ("Kalpetta", "KERALA"),
    "673301": ("Malappuram", "KERALA"),
    "673302": ("Manjeri", "KERALA"),
    "673303": ("Tirur", "KERALA"),
    "673304": ("Ponnani", "KERALA"),
    "673305": ("Perinthalmanna", "KERALA"),
    "673306": ("Kondotty", "KERALA"),
    "673307": ("Nilambur", "KERALA"),
    "673308": ("Parappanangadi", "KERALA"),
    "673309": ("Tanur", "KERALA"),
    "673310": ("Tirurrangadi", "KERALA"),
    "673315": ("Malappuram", "KERALA"),
    "673316": ("Malappuram", "KERALA"),
    "673317": ("Malappuram", "KERALA"),
    "673318": ("Malappuram", "KERALA"),
    "673319": ("Malappuram", "KERALA"),
    "673320": ("Malappuram", "KERALA"),
    "673321": ("Malappuram", "KERALA"),
    "673501": ("Palakkad", "KERALA"),
    "673502": ("Palakkad", "KERALA"),
    "673503": ("Palakkad", "KERALA"),
    "673504": ("Palakkad", "KERALA"),
    "673505": ("Palakkad", "KERALA"),
    "673506": ("Palakkad", "KERALA"),
    "673507": ("Ottapalam", "KERALA"),
    "673508": ("Alathur", "KERALA"),
    "673509": ("Shoranur", "KERALA"),
    "673510": ("Chittur", "KERALA"),
    "673511": ("Mannarkkad", "KERALA"),
    "673512": ("Malampuzha", "KERALA"),
    "673513": ("Nemmara", "KERALA"),
    "673514": ("Pattambi", "KERALA"),
    "673515": ("Palakkad", "KERALA"),
    "673516": ("Palakkad", "KERALA"),
    # Thrissur
    "673601": ("Thrissur", "KERALA"),
    "673602": ("Thrissur", "KERALA"),
    "673603": ("Thrissur", "KERALA"),
    "673604": ("Guruvayur", "KERALA"),
    "673605": ("Kodungallur", "KERALA"),
    "673606": ("Chalakudy", "KERALA"),
    "673608": ("Wadakkancherry", "KERALA"),
    "673611": ("Kunnamkulam", "KERALA"),
    "673612": ("Irinjalakuda", "KERALA"),
    # Ernakulam / Kochi
    "673001": ("Ernakulam", "KERALA"),
    "682001": ("Kochi", "KERALA"),
    "682002": ("Kochi", "KERALA"),
    "682003": ("Kochi", "KERALA"),
    "682004": ("Kochi", "KERALA"),
    "682005": ("Ernakulam", "KERALA"),
    "682006": ("Ernakulam", "KERALA"),
    "682007": ("Ernakulam", "KERALA"),
    "682008": ("Ernakulam", "KERALA"),
    "682009": ("Ernakulam", "KERALA"),
    "682010": ("Ernakulam", "KERALA"),
    "682011": ("Aluva", "KERALA"),
    "682012": ("Thrippunithura", "KERALA"),
    "682013": ("Edapally", "KERALA"),
    "682014": ("Kakkanad", "KERALA"),
    "682015": ("Kalamassery", "KERALA"),
    "682016": ("North Paravur", "KERALA"),
    "682017": ("Angamaly", "KERALA"),
    "682018": ("Perumbavoor", "KERALA"),
    "682019": ("Muvattupuzha", "KERALA"),
    "682020": ("Kothamangalam", "KERALA"),
    # Thiruvananthapuram
    "695001": ("Thiruvananthapuram", "KERALA"),
    "695002": ("Thiruvananthapuram", "KERALA"),
    "695003": ("Thiruvananthapuram", "KERALA"),
    "695004": ("Thiruvananthapuram", "KERALA"),
    "695005": ("Thiruvananthapuram", "KERALA"),
    "695006": ("Thiruvananthapuram", "KERALA"),
    "695007": ("Thiruvananthapuram", "KERALA"),
    "695008": ("Thiruvananthapuram", "KERALA"),
    "695009": ("Thiruvananthapuram", "KERALA"),
    "695010": ("Thiruvananthapuram", "KERALA"),
    "695011": ("Thiruvananthapuram", "KERALA"),
    "695012": ("Thiruvananthapuram", "KERALA"),
    "695013": ("Thiruvananthapuram", "KERALA"),
    "695014": ("Thiruvananthapuram", "KERALA"),
    "695015": ("Thiruvananthapuram", "KERALA"),
    "695016": ("Thiruvananthapuram", "KERALA"),
    "695017": ("Thiruvananthapuram", "KERALA"),
    "695018": ("Neyyattinkara", "KERALA"),
    "695019": ("Attingal", "KERALA"),
    "695020": ("Nedumangad", "KERALA"),
    "695021": ("Varkala", "KERALA"),
    # Kollam
    "691001": ("Kollam", "KERALA"),
    "691002": ("Kollam", "KERALA"),
    "691003": ("Kollam", "KERALA"),
    "691004": ("Kollam", "KERALA"),
    "691005": ("Kollam", "KERALA"),
    "691006": ("Kollam", "KERALA"),
    "691007": ("Kollam", "KERALA"),
    "691008": ("Punalur", "KERALA"),
    "691009": ("Karunagappally", "KERALA"),
    "691010": ("Kottarakkara", "KERALA"),
    # Alappuzha
    "688001": ("Alappuzha", "KERALA"),
    "688002": ("Alappuzha", "KERALA"),
    "688003": ("Cherthala", "KERALA"),
    "688004": ("Chengannur", "KERALA"),
    "688005": ("Kuttanad", "KERALA"),
    "688006": ("Mavelikara", "KERALA"),
    "688007": ("Kayamkulam", "KERALA"),
    "688008": ("Haripad", "KERALA"),
    # Kottayam
    "686001": ("Kottayam", "KERALA"),
    "686002": ("Kottayam", "KERALA"),
    "686003": ("Kottayam", "KERALA"),
    "686004": ("Changanacherry", "KERALA"),
    "686005": ("Pala", "KERALA"),
    "686006": ("Ettumanoor", "KERALA"),
    "686007": ("Vaikom", "KERALA"),
    "686008": ("Meenachil", "KERALA"),
    # Idukki
    "685001": ("Thodupuzha", "KERALA"),
    "685002": ("Munnar", "KERALA"),
    "685003": ("Nedumkandam", "KERALA"),
    "685004": ("Kattappana", "KERALA"),
    "685005": ("Kumily", "KERALA"),
    "685006": ("Adimali", "KERALA"),
    # Pathanamthitta
    "689001": ("Pathanamthitta", "KERALA"),
    "689002": ("Thiruvalla", "KERALA"),
    "689003": ("Ranni", "KERALA"),
    "689004": ("Adoor", "KERALA"),
    "689005": ("Pandalam", "KERALA"),
    "689006": ("Tiruvalla", "KERALA"),
    # Kannur
    "670001": ("Kannur", "KERALA"),
    "670002": ("Kannur", "KERALA"),
    "670003": ("Kannur", "KERALA"),
    "670004": ("Thalassery", "KERALA"),
    "670005": ("Iritty", "KERALA"),
    "670006": ("Mattannur", "KERALA"),
    "670007": ("Koothuparamba", "KERALA"),
    "670008": ("Kuthuparamba", "KERALA"),
    "670009": ("Taliparamba", "KERALA"),
    "670010": ("Payyanur", "KERALA"),
    # Kasaragod
    "671001": ("Kasaragod", "KERALA"),
    "671002": ("Kasaragod", "KERALA"),
    "671003": ("Kanhangad", "KERALA"),
    "671004": ("Kasaragod", "KERALA"),
    "671005": ("Kasaragod", "KERALA"),
    "671006": ("Kasaragod", "KERALA"),
    # Wayanad
    "673121": ("Kalpetta", "KERALA"),
    "673122": ("Mananthavady", "KERALA"),
    "673123": ("Sultan Bathery", "KERALA"),
    "673124": ("Kalpetta", "KERALA"),
    "673212": ("Mananthavady", "KERALA"),
    # Palakkad
    "678001": ("Palakkad", "KERALA"),
    "678002": ("Palakkad", "KERALA"),
    "678003": ("Palakkad", "KERALA"),
    "678004": ("Palakkad", "KERALA"),
    "678005": ("Palakkad", "KERALA"),
    "678006": ("Palakkad", "KERALA"),
    "678007": ("Ottapalam", "KERALA"),
    "678008": ("Shoranur", "KERALA"),
    "678009": ("Pattambi", "KERALA"),
    "678010": ("Mannarkkad", "KERALA"),
    "678011": ("Alathur", "KERALA"),
    "678012": ("Chittur", "KERALA"),
    "678013": ("Nemmara", "KERALA"),
    "678014": ("Malampuzha", "KERALA"),
}

def lookup_pincode(pin: str):
    """Return (city, state) for a Kerala pincode, or (None, None)."""
    return KERALA_PINCODES.get(pin.strip(), (None, None))

# ── IMPROVEMENT 1: loyalty badge helper ───────────────────────────────────────
def loyalty_badge(tier):
    badges = {
        "Gold":   ("🥇", "#c9a96e", "#2a1a0e"),
        "Silver": ("🥈", "#b0b8c1", "#1a1f24"),
        "Bronze": ("🥉", "#cd7f32", "#1f1208"),
    }
    if tier in badges:
        icon, color, bg = badges[tier]
        return (f"<span style='background:{bg}; color:{color}; "
                f"border:1px solid {color}55; border-radius:20px; "
                f"padding:2px 10px; font-size:0.8rem; font-weight:600; "
                f"white-space:nowrap;'>{icon} {tier}</span>")
    return f"<span style='color:#aaa; font-size:0.85rem;'>{tier or '—'}</span>"

# ─────────────────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs([
    "➕ Register Customer",
    "📋 Customer List",
    "🔍 Search Customer"
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — REGISTER
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.subheader("Register New Customer")

    # ── IMPROVEMENT 3: pincode auto-fill (outside form so it reacts live) ────
    st.markdown("**Quick Fill — Enter Pincode First**")
    pin_col, hint_col = st.columns([2, 3])
    with pin_col:
        quick_pin = st.text_input(
            "Pincode (Kerala auto-fill)",
            placeholder="e.g. 673106",
            max_chars=6,
            key="quick_pin"
        )
    with hint_col:
        if quick_pin and len(quick_pin) == 6:
            auto_city, auto_state = lookup_pincode(quick_pin)
            if auto_city:
                st.success(f"✅ Found: **{auto_city}**, {auto_state}")
            else:
                auto_city, auto_state = "", ""
                st.info("Pincode not in Kerala list — fill city/state manually.")
        else:
            auto_city, auto_state = "", ""

    st.divider()

    with st.form("reg_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            name    = st.text_input("Full Name *")
            email   = st.text_input("Email Address")
            phone   = st.text_input("Phone Number (10 digits) *")
        with c2:
            age     = st.number_input("Age *", min_value=1, max_value=100, value=25)
            city    = st.text_input("City", value=auto_city)
            state   = st.text_input("State", value=auto_state)
            pincode = st.text_input("Pincode", value=quick_pin)
        address   = st.text_area("Address")
        submitted = st.form_submit_button("✅ Register Customer",
                                           use_container_width=True)

    if submitted:
        errors = []
        if not name.strip():
            errors.append("Name is required.")
        if not phone.strip():
            errors.append("Phone is required.")
        elif not phone.isdigit() or len(phone) != 10:
            errors.append("Phone must be exactly 10 digits.")
        if email and "@" not in email:
            errors.append("Enter a valid email address.")

        if errors:
            for e in errors:
                st.error(e)
        elif check_duplicate_customer(phone.strip(), email.strip()):
            st.warning("⚠️ A customer with this phone or email already exists.")
        else:
            cid = insert_customer(
                name.strip(), email.strip(), phone.strip(),
                'W', int(age), address.strip(),
                city.strip(), state.strip(), pincode.strip()
            )
            st.success(f"🎉 Customer registered! Customer ID: **{cid}**")
            st.balloons()

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — CUSTOMER LIST
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.subheader("All Registered Customers")
    df = get_all_customers()

    if df.empty:
        st.info("No customers registered yet.")
    else:
        # KPI row
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Customers", len(df))
        age_groups = df['age_group'].value_counts() if 'age_group' in df.columns else {}
        c2.metric("Young Adults",  int(age_groups.get('Young Adult', 0)))
        c3.metric("Adults",        int(age_groups.get('Adult', 0)))
        c4.metric("Avg Age",       f"{df['age'].mean():.1f}")

        st.divider()

        # ── IMPROVEMENT 4: search/filter bar above dataframe ─────────────────
        sf1, sf2 = st.columns([3, 2])
        with sf1:
            list_search = st.text_input(
                "🔍 Filter by Name or City",
                placeholder="Type to filter...",
                key="list_search"
            )
        with sf2:
            tier_filter = st.selectbox(
                "Loyalty Tier",
                ["All", "Gold", "Silver", "Bronze"],
                key="tier_filter"
            )

        # Apply filters
        filtered = df.copy()
        if list_search:
            mask = (
                filtered["name"].str.contains(list_search, case=False, na=False) |
                filtered["city"].str.contains(list_search, case=False, na=False)
            )
            filtered = filtered[mask]
        if tier_filter != "All":
            filtered = filtered[filtered["loyalty_tier"] == tier_filter]

        st.caption(f"Showing {len(filtered):,} of {len(df):,} customers")

        # ── IMPROVEMENT 1: loyalty tier badges ───────────────────────────────
        # Build display dataframe with badge column
        display_cols = ["cust_id", "name", "age", "age_group",
                        "phone", "email", "city", "state",
                        "loyalty_tier", "created_at"]
        display_cols = [c for c in display_cols if c in filtered.columns]

        if filtered.empty:
            st.info("No customers match your filter.")
        else:
            # Render loyalty badges as HTML in a styled table
            # Show plain dataframe first then badges below
            st.dataframe(
                filtered[display_cols],
                use_container_width=True,
                height=400,
                column_config={
                    "cust_id":      st.column_config.NumberColumn("ID", width="small"),
                    "name":         st.column_config.TextColumn("Name", width="medium"),
                    "age":          st.column_config.NumberColumn("Age", width="small"),
                    "age_group":    st.column_config.TextColumn("Age Group", width="small"),
                    "phone":        st.column_config.TextColumn("Phone"),
                    "email":        st.column_config.TextColumn("Email"),
                    "city":         st.column_config.TextColumn("City"),
                    "state":        st.column_config.TextColumn("State"),
                    "loyalty_tier": st.column_config.TextColumn("Loyalty"),
                    "created_at":   st.column_config.TextColumn("Registered"),
                }
            )

            # Loyalty tier badge summary below the table
            st.markdown("**Loyalty Tier Breakdown:**")
            badge_cols = st.columns(3)
            gold_n   = len(filtered[filtered["loyalty_tier"] == "Gold"])
            silver_n = len(filtered[filtered["loyalty_tier"] == "Silver"])
            bronze_n = len(filtered[filtered["loyalty_tier"] == "Bronze"])
            badge_cols[0].markdown(
                f"{loyalty_badge('Gold')} &nbsp; **{gold_n}** customers",
                unsafe_allow_html=True
            )
            badge_cols[1].markdown(
                f"{loyalty_badge('Silver')} &nbsp; **{silver_n}** customers",
                unsafe_allow_html=True
            )
            badge_cols[2].markdown(
                f"{loyalty_badge('Bronze')} &nbsp; **{bronze_n}** customers",
                unsafe_allow_html=True
            )

        csv = filtered.to_csv(index=False).encode()
        st.download_button(
            "⬇️ Export Filtered CSV", csv,
            "customers_filtered.csv", "text/csv"
        )

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — SEARCH
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.subheader("Search Customer")

    col_a, col_b = st.columns([3, 1])
    with col_a:
        search_val = st.text_input(
            "Search by Name, Phone, or Customer ID"
        )
    with col_b:
        search_btn = st.button("🔍 Search", use_container_width=True)

    if search_btn and search_val:
        result = run_query(f"""
            SELECT c.*,
                   COUNT(o.order_id) AS total_orders,
                   SUM(o.amount)     AS total_spent
            FROM customers c
            LEFT JOIN orders o ON c.cust_id = o.cust_id
            WHERE c.name  LIKE '%{search_val}%'
               OR c.phone LIKE '%{search_val}%'
               OR CAST(c.cust_id AS TEXT) = '{search_val}'
            GROUP BY c.cust_id
        """)

        if result.empty:
            st.warning("No customer found.")
        else:
            for _, row in result.iterrows():
                tier_html = loyalty_badge(row.get("loyalty_tier", ""))
                with st.expander(
                    f"👤 {row['name']}  |  ID: {row['cust_id']}  |  "
                    f"{row.get('city', '')}",
                    expanded=True
                ):
                    # ── Customer summary ──────────────────────────────────────
                    r1, r2, r3 = st.columns(3)
                    r1.markdown(
                        f"**Age:** {row['age']} ({row.get('age_group','')})"
                    )
                    r2.markdown(
                        f"**Phone:** {row['phone']}  \n"
                        f"**Email:** {row.get('email','—')}"
                    )
                    r3.markdown(
                        f"**Orders:** {int(row.get('total_orders',0))}  \n"
                        f"**Total Spent:** ₹{float(row.get('total_spent',0) or 0):,.0f}"
                    )

                    # Loyalty badge
                    st.markdown(
                        f"**Loyalty Tier:** {tier_html}",
                        unsafe_allow_html=True
                    )

                    st.divider()

                    # ── IMPROVEMENT 2: Full order history ─────────────────────
                    st.markdown("**📦 Order History**")
                    orders_df = run_query(f"""
                        SELECT
                            order_id,
                            order_date,
                            category,
                            size,
                            qty,
                            amount,
                            status,
                            retail_supplier,
                            ship_state,
                            return_flag
                        FROM orders
                        WHERE cust_id = {row['cust_id']}
                        ORDER BY order_date DESC
                    """)

                    if orders_df.empty:
                        st.info("No orders found for this customer.")
                    else:
                        # Summary metrics
                        m1, m2, m3, m4 = st.columns(4)
                        m1.metric("Total Orders",
                                  f"{len(orders_df):,}")
                        m2.metric("Total Spent",
                                  f"₹{orders_df['amount'].sum():,.0f}")
                        m3.metric("Avg Order",
                                  f"₹{orders_df['amount'].mean():,.0f}")
                        m4.metric("Returns",
                                  int(orders_df['return_flag'].sum()))

                        # Colour-code status column
                        def status_color(val):
                            c = {
                                "Delivered": "background-color:#0d3b2e;color:#2ecc71",
                                "Cancelled": "background-color:#3b0d0d;color:#e74c3c",
                                "Returned":  "background-color:#3b2a0d;color:#f39c12",
                                "Shipped":   "background-color:#0d2a3b;color:#3498db",
                                "Pending":   "background-color:#1a1a3b;color:#9b59b6",
                            }
                            return c.get(val, "")

                        styled = orders_df.style.applymap(
                            status_color, subset=["status"]
                        ).format({"amount": "₹{:,.0f}"})

                        st.dataframe(styled, use_container_width=True,
                                     height=min(350, 60 + len(orders_df) * 35))

                        # Download this customer's orders
                        csv = orders_df.to_csv(index=False).encode()
                        st.download_button(
                            f"⬇️ Export {row['name']}'s Orders",
                            csv,
                            f"orders_cust_{row['cust_id']}.csv",
                            "text/csv",
                            key=f"dl_{row['cust_id']}"
                        )
