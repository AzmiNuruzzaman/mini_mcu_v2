# auth/login_ui.py
import streamlit as st
from pathlib import Path
from PIL import Image
from auth.auth import get_user_by_username
from auth.session_manager import save_session  # Already imported
import bcrypt
from config.settings import APP_TITLE

def login():
    """
    Display login UI at top-level. Handles setting session_state keys
    for authenticated users. Works for Manager, Tenaga Kesehatan, and Master.
    """

    BASE_DIR = Path(__file__).resolve().parent.parent
    LOGO_PATH = BASE_DIR / "assets/logo.png"

    # Display logo
    try:
        logo = Image.open(LOGO_PATH)
        st.image(logo, width=250)
    except FileNotFoundError:
        st.warning("⚠️ Logo not found. Please place 'logo.png' in the assets folder.")

    st.markdown("### Selamat datang di Mini-MCU")
    st.markdown("<br>", unsafe_allow_html=True)

    # -------------------------------
    # Login form
    # -------------------------------
    with st.form("login_form", clear_on_submit=False):
        username = st.text_input("User ID", placeholder="Masukkan ID Anda")
        password = st.text_input("Password", type="password", placeholder="Masukkan Password")
        submit = st.form_submit_button("Login")  # allows Enter key submission

    # -------------------------------
    # Handle form submission
    # -------------------------------
    if submit:
        if not username or not password:
            st.warning("⚠️ Harap isi username dan password")
            return

        result = get_user_by_username(username)
        if result and bcrypt.checkpw(password.encode("utf-8"), result["password"].encode("utf-8")):
            # Set session state keys
            st.session_state["authenticated"] = True
            st.session_state["user_role"] = result["role"]
            st.session_state["username"] = username
            st.session_state["employee_uid"] = result.get("uid")  # if applicable
            st.session_state["current_page"] = result["role"]  # initial page to show
            st.session_state["login_success"] = True

            # 🔑 Save session for persistence across refresh
            save_session(username, result["role"], result.get("uid"))

            # Optional: set query params if you want URL persistence
            st.query_params["user"] = username
            st.query_params["role"] = result["role"]
            if result.get("uid"):
                st.query_params["uid"] = result.get("uid")

            # Force immediate rerun so user is redirected to the main app
            st.rerun()

        else:
            st.error("❌ Username atau password salah!")
