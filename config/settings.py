# config/settings.py

# ---------------------------
# App UI Titles
# ---------------------------
APP_TITLE = "🏥 Mini MCU Web App"
SIDEBAR_TITLE = "🔑 Login"

# ---------------------------
# Postgres / Supabase connection (V2)
# ---------------------------
POSTGRES_URL = "postgresql+psycopg2://mini_mcu_user:new_password@localhost:5432/mini_mcu_v2"


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
