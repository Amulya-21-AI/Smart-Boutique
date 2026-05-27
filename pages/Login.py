"""pages/Login.py — Login and Customer Self-Registration"""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import streamlit as st
from database.db import (init_db, ensure_default_admin, authenticate_user,
                          create_user, insert_customer, check_duplicate_customer,
                          get_user_by_email, username_exists)
from utils.auth import GLOBAL_CSS

st.set_page_config(
    page_title="Login · AMK Fashion Hub",
    page_icon="🧵",
    layout="centered",
    initial_sidebar_state="collapsed"
)

init_db()
ensure_default_admin()

st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

# Redirect if already logged in
if st.session_state.get('authenticated'):
    st.switch_page("Main.py")

# ── Hero header ───────────────────────────────────────────────────────────────
st.markdown("""
<div style='text-align:center;padding:2rem 0 1.5rem;'>
  <div style='font-size:3rem;'>🧵</div>
  <h1 style='color:#c9a96e;margin:0;font-size:2.2rem;'>AMK Fashion Hub</h1>
  <p style='color:#888;margin-top:0.3rem;'>Anjali Ladies Boutique · Muggam, Kerala</p>
</div>
""", unsafe_allow_html=True)

tab_login, tab_register = st.tabs(["🔐 Login", "📝 Register as Customer"])

# ══════════════════════════════════════════════════════════════════════════════
# LOGIN
# ══════════════════════════════════════════════════════════════════════════════
with tab_login:
    st.markdown("#### Welcome back")

    with st.form("login_form"):
        username = st.text_input("Username", placeholder="Enter your username")
        password = st.text_input("Password", type="password", placeholder="••••••••")
        login_btn = st.form_submit_button("🔑 Login", use_container_width=True)

    if login_btn:
        if not username.strip() or not password:
            st.error("Please enter both username and password.")
        else:
            user = authenticate_user(username.strip(), password)
            if user:
                st.session_state['authenticated'] = True
                st.session_state['user_id']       = user['user_id']
                st.session_state['username']      = user['username']
                st.session_state['role']          = user['role']
                st.session_state['cust_id']       = user.get('cust_id')
                st.session_state['user_email']    = user.get('email', '')
                st.success(f"Welcome back, {user['username']}!")
                st.switch_page("Main.py")
            else:
                st.error("Invalid username or password. Please try again.")

    st.markdown("---")
    st.info(
        "**First-time admin?**  \n"
        "Username: `admin` · Password: `admin123`  \n"
        "*(Please change after first login)*"
    )

# ══════════════════════════════════════════════════════════════════════════════
# REGISTER
# ══════════════════════════════════════════════════════════════════════════════
with tab_register:
    st.markdown("#### Create your customer account")
    st.info(
        "Register once and get your **Customer ID instantly**. "
        "Use it to place orders, track deliveries, and get personalised recommendations."
    )

    with st.form("reg_form", clear_on_submit=False):
        c1, c2 = st.columns(2)
        with c1:
            r_name     = st.text_input("Full Name *")
            r_email    = st.text_input("Email Address *")
            r_phone    = st.text_input("Phone Number * (10 digits)")
            r_age      = st.number_input("Age *", min_value=10, max_value=100, value=25)
        with c2:
            r_username = st.text_input("Choose Username *")
            r_password = st.text_input("Password * (min 6 chars)", type="password")
            r_confirm  = st.text_input("Confirm Password *", type="password")
            r_city     = st.text_input("City", placeholder="e.g. Muggam")

        r_address = st.text_area("Address (optional)", height=70)

        reg_btn = st.form_submit_button("✅ Create Account & Get Customer ID",
                                         use_container_width=True)

    if reg_btn:
        errors = []
        if not r_name.strip():
            errors.append("Full Name is required.")
        if not r_email.strip() or "@" not in r_email:
            errors.append("A valid Email Address is required.")
        if not r_phone.strip() or not r_phone.strip().isdigit() or len(r_phone.strip()) != 10:
            errors.append("Phone must be exactly 10 digits.")
        if not r_username.strip():
            errors.append("Username is required.")
        elif username_exists(r_username.strip()):
            errors.append("Username already taken — please choose another.")
        if len(r_password) < 6:
            errors.append("Password must be at least 6 characters.")
        if r_password != r_confirm:
            errors.append("Passwords do not match.")

        if errors:
            for e in errors:
                st.error(e)
        elif check_duplicate_customer(r_phone.strip(), r_email.strip()):
            st.warning(
                "A customer with this phone or email already exists. "
                "Please use the Login tab instead."
            )
        elif get_user_by_email(r_email.strip()):
            st.warning("This email is already registered. Please log in.")
        else:
            cust_id = insert_customer(
                r_name.strip(), r_email.strip(), r_phone.strip(),
                'W', int(r_age), r_address.strip(),
                r_city.strip(), 'KERALA', ''
            )
            try:
                create_user(r_username.strip(), r_email.strip(),
                            r_password, 'customer', cust_id)

                st.success("Account created! Save your details below.")
                st.balloons()
                st.markdown(f"""
<div style='background:linear-gradient(135deg,#1a0a2e,#16213e);
            border:2px solid #c9a96e66;border-radius:14px;padding:1.5rem;
            margin-top:1rem;'>
  <div style='color:#c9a96e;font-size:1.2rem;font-weight:700;
              margin-bottom:1rem;'>🎉 Registration Successful</div>
  <table style='width:100%;font-size:0.95rem;'>
    <tr>
      <td style='color:#aaa;padding:6px 0;width:40%;'>Customer ID</td>
      <td style='color:#fff;font-weight:700;font-size:1.3rem;'>
        <code style='background:#c9a96e22;padding:4px 12px;
                      border-radius:6px;color:#c9a96e;'>CUST-{cust_id}</code>
      </td>
    </tr>
    <tr>
      <td style='color:#aaa;padding:6px 0;'>Username</td>
      <td style='color:#f5e6d3;'>{r_username.strip()}</td>
    </tr>
    <tr>
      <td style='color:#aaa;padding:6px 0;'>Name</td>
      <td style='color:#f5e6d3;'>{r_name.strip()}</td>
    </tr>
    <tr>
      <td style='color:#aaa;padding:6px 0;'>Phone</td>
      <td style='color:#f5e6d3;'>{r_phone.strip()}</td>
    </tr>
  </table>
  <div style='margin-top:1rem;padding:0.8rem;background:#ffffff08;
              border-radius:8px;color:#aaa;font-size:0.85rem;'>
    📌 Note your Customer ID <b style='color:#c9a96e;'>CUST-{cust_id}</b>.
    You will need it when placing orders.
  </div>
</div>
""", unsafe_allow_html=True)
                st.info("You can now log in with your new credentials.")
            except Exception as exc:
                if "UNIQUE" in str(exc):
                    st.error("Username already taken. Please choose a different username.")
                else:
                    st.error(f"Registration failed: {exc}")
