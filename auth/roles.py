# auth/roles.py
import streamlit as st

# -----------------------------
# Role Check Helpers
# -----------------------------

def is_master() -> bool:
    """Return True if the logged-in user is Master."""
    return st.session_state.get("user_role") == "Master"

def is_manager() -> bool:
    """Return True if the logged-in user is Manager."""
    return st.session_state.get("user_role") == "Manager"

def is_nurse() -> bool:
    """Return True if the logged-in user is Tenaga Kesehatan."""
    return st.session_state.get("user_role") == "Tenaga Kesehatan"

def has_login_access() -> bool:
    """Return True if user role is one that can log in (master/manager/nurse)."""
    return st.session_state.get("user_role") in ["Master", "Manager", "Tenaga Kesehatan"]
