# -------------------------------
# app_karyawan.py (Dedicated QR login)
# -------------------------------

import streamlit as st
from pathlib import Path
from PIL import Image
from db.queries import get_employee_by_uid
from ui.karyawan_interface import karyawan_interface
from config.settings import APP_TITLE

# -------------------------------
# Page config
# -------------------------------
st.set_page_config(page_title=APP_TITLE + " - Karyawan", layout="wide")

# -------------------------------
# 0️⃣ Skip if already QR session active
# -------------------------------
if st.session_state.get("qr_access") and st.session_state.get("authenticated"):
    karyawan_interface(uid=st.session_state.get("employee_uid"))
    st.stop()

# -------------------------------
# 1️⃣ Read UID from URL query params
# -------------------------------
params = st.query_params
uid = params.get("uid", [None])[0] if isinstance(params.get("uid"), list) else params.get("uid")

if not uid:
    st.warning("⚠️ UID tidak ditemukan. Harap gunakan QR code yang diberikan oleh manager.")
    st.stop()

# -------------------------------
# 2️⃣ Fetch employee from database
# -------------------------------
employee = get_employee_by_uid(uid)
if not employee:
    st.error("❌ UID tidak valid atau karyawan tidak ditemukan.")
    st.stop()

# -------------------------------
# 3️⃣ Set session_state for Karyawan
# -------------------------------
st.session_state.update({
    "user_role": "Karyawan",
    "username": employee["nama"],
    "employee_uid": uid,
    "qr_access": True,
    "authenticated": True,
    "current_page": "Karyawan"
})

# -------------------------------
# 4️⃣ Display logo and welcome
# -------------------------------
BASE_DIR = Path(__file__).resolve().parent
LOGO_PATH = BASE_DIR / "assets/logo.png"

try:
    logo = Image.open(LOGO_PATH)
    st.image(logo, width=200)
except FileNotFoundError:
    st.warning("⚠️ Logo tidak ditemukan.")

st.markdown(f"### Selamat datang, {employee['nama']}")

# -------------------------------
# 5️⃣ Render Karyawan interface
# -------------------------------
karyawan_interface(uid=uid)

# -------------------------------
# 6️⃣ Stop further rendering
# -------------------------------
st.stop()
