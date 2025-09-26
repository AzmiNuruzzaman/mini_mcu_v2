# -------------------------------
# app.py (V2 – With session persistence)
# -------------------------------

import streamlit as st
from auth.login_ui import login
from auth.session_manager import load_session, clear_session  # <- ADD THIS IMPORT
from ui.nurse_interface import nurse_interface
from ui.manager_interface import manager_interface
from ui.master_interface import master_interface
from config.settings import APP_TITLE

st.set_page_config(page_title=APP_TITLE, layout="wide")

# -------------------------------
# Initialize session_state keys at top-level
# -------------------------------
for key in ["authenticated", "user_role", "username", "employee_uid", "current_page"]:
    if key not in st.session_state:
        st.session_state[key] = False if key == "authenticated" else None

# -------------------------------
# CHECK FOR EXISTING SESSION ON APP START - ADD THIS SECTION
# -------------------------------
if not st.session_state.get("authenticated"):
    saved_session = load_session()
    if saved_session:
        st.session_state["authenticated"] = True
        st.session_state["user_role"] = saved_session["user_role"]
        st.session_state["username"] = saved_session["username"]
        st.session_state["employee_uid"] = saved_session.get("employee_uid")
        st.session_state["current_page"] = saved_session["user_role"]

# -------------------------------
# Sidebar for logged-in users
# -------------------------------
def render_sidebar():
    with st.sidebar:
        st.write(f"👤 Logged in sebagai: {st.session_state.get('username', '-')}")
        if st.button("Logout"):
            # Clear session file - ADD THIS LINE
            clear_session()
            # Clear all session state
            for key in ["authenticated", "user_role", "username", "employee_uid", "current_page"]:
                st.session_state[key] = False if key == "authenticated" else None
            # Force rerun to immediately show login page
            st.rerun()

# -------------------------------
# Main function
# -------------------------------
def main():
    # -------------------------------
    # Show interface if authenticated
    # -------------------------------
    if st.session_state.get("authenticated"):
        render_sidebar()
        role = st.session_state["user_role"]

        # Decide which interface to show
        page_to_show = st.session_state.get("current_page") or role

        if page_to_show == "Manager":
            st.session_state["current_page"] = "Manager"
            manager_interface()
        elif page_to_show == "Tenaga Kesehatan":
            st.session_state["current_page"] = "Tenaga Kesehatan"
            nurse_interface()
        elif page_to_show == "Master":
            st.session_state["current_page"] = "Master"
            master_interface()
        else:
            st.error("❌ Role tidak dikenal, hubungi administrator.")

    # -------------------------------
    # Else, show login UI at top level
    # -------------------------------
    else:
        login()  # ✅ uses login_ui.login() for normal login

# -------------------------------
# Run app
# -------------------------------
if __name__ == "__main__":
    main()