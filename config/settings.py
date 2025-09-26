# config/settings.py

# ---------------------------
# App UI Titles
# ---------------------------
APP_TITLE = "🏥 Mini MCU Web App"
SIDEBAR_TITLE = "🔑 Login"

# ---------------------------
# Postgres / Supabase connection (V2)
# ---------------------------
import streamlit as st

POSTGRES_URL = (
    f"postgresql://{st.secrets['USER']}:"
    f"{st.secrets['PASSWORD']}@"
    f"{st.secrets['HOST']}:"
    f"{st.secrets['PORT']}/"
    f"{st.secrets['DBNAME']}?sslmode=require"
)

# ---------------------------
# Default users (for login only)
# ---------------------------
# Only include accounts that actually log in.
# Karyawan do NOT log in; they are uploaded via XLS.
DEFAULT_USERS = [
    ("master", "master123", "Master"),        # super-admin
    ("manager", "manager123", "Manager"),     # default manager
    ("nurse", "nurse123", "Tenaga Kesehatan") # default nurse
]

UPLOAD_DIR = "uploads"  # folder to store uploaded XLS/CSV files

# ---------------------------
# File export configs
# ---------------------------
CSV_FILENAME = "medical_checkup_data.csv"
EXCEL_FILENAME = "medical_checkup_data.xlsx"

# ---------------------------
# INITIAL LOKASI SEEDS
# ---------------------------
INITIAL_LOKASI = [
    "Rig AB-100",
    "Rig LTO-150",
    "Rig Taylor C-200",
    "HWU EHR#10",
    "Kantor"
]
