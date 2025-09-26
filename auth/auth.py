# auth/auth.py
import streamlit as st
import bcrypt
from db.queries import get_user_by_username
from auth.roles import has_login_access

# -------------------------------------------------------------------
# Session Helpers
# -------------------------------------------------------------------
def set_session(user: dict):
    """Store user info in session state."""
    st.session_state["username"] = user["username"]
    st.session_state["user_role"] = user["role"]
    st.session_state["qr_access"] = False  # always False for manual login
    st.session_state["authenticated"] = True

def clear_session():
    """Clear session state."""
    for key in ["username", "user_role", "qr_access", "authenticated"]:
        if key in st.session_state:
            del st.session_state[key]

def is_authenticated() -> bool:
    """Return True if a user is logged in."""
    return st.session_state.get("authenticated", False)

def get_current_user() -> dict | None:
    """Return current logged-in user info or None."""
    if is_authenticated():
        return {
            "username": st.session_state["username"],
            "role": st.session_state["user_role"]
        }
    return None

# -------------------------------------------------------------------
# Login / Logout Logic
# -------------------------------------------------------------------
def login_user(username: str, password: str) -> bool:
    """
    Attempt login for a user.
    Returns True if successful, False otherwise.
    """
    user = get_user_by_username(username)
    if user and bcrypt.checkpw(password.encode("utf-8"), user["password"].encode("utf-8")):
        if not has_login_access():
            st.error("❌ Anda tidak memiliki akses login saat ini.")
            return False
        set_session(user)
        # ✅ Show only login success
        st.success(f"✅ Login berhasil! Selamat datang, {user['username']}.")
        return True
    st.error("❌ Username atau password salah.")
    return False

def logout():
    """Logout the current user and clear session state."""
    clear_session()
    # ✅ Show only logout message
    st.info("ℹ️ Logout berhasil. Sampai jumpa!")

