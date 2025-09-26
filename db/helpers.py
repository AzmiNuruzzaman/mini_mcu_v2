# db/helpers.py
from db.database import get_engine
from sqlalchemy import text
import pandas as pd
from db.queries import get_employees, get_latest_medical_checkup

# ---------------------------
# Lokasi Helpers
# ---------------------------

def get_all_lokasi():
    """
    Return a list of all lokasi names in the database, sorted alphabetically.
    """
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("SELECT name FROM lokasi ORDER BY name"))
        return [row[0] for row in result.fetchall()]

def validate_lokasi(lokasi_name: str) -> bool:
    """
    Check if the given lokasi is non-empty.
    Returns True if valid, False otherwise.
    """
    return bool(lokasi_name and lokasi_name.strip())

# ---------------------------
# DataFrame Helpers
# ---------------------------

def sanitize_df_for_display(df: pd.DataFrame) -> pd.DataFrame:
    """
    Prepare DataFrame for Streamlit display.
    Converts UUIDs, dates, and other non-serializable types to strings.
    """
    df_safe = df.copy()

    for col in df_safe.columns:
        # Convert UUID objects to string
        if df_safe[col].dtype == 'object':
            if df_safe[col].apply(lambda x: hasattr(x, 'hex') if x is not None else False).any():
                df_safe[col] = df_safe[col].apply(lambda x: str(x) if x is not None else '')
            else:
                # Convert any remaining non-string objects safely
                df_safe[col] = df_safe[col].apply(lambda x: str(x) if pd.notna(x) else '')

        # Convert datetime/date objects to string
        if pd.api.types.is_datetime64_any_dtype(df_safe[col]):
            df_safe[col] = df_safe[col].apply(lambda x: x.strftime('%Y-%m-%d') if pd.notna(x) else '')

    return df_safe

# ---------------------------
# Dashboard / Tab Helpers
# ---------------------------

def get_dashboard_checkup_data() -> pd.DataFrame:
    """
    Return the combined employees + latest_checkup DataFrame,
    ready for Tab1/Subtab1 and Tab6/Subtab1 in Manager Interface.
    """
    employees_df = get_employees()
    latest_checkup_df = get_latest_medical_checkup()
    if latest_checkup_df is None or latest_checkup_df.empty:
        latest_checkup_df = pd.DataFrame()

    df_combined = employees_df.copy()

    # --- PATCH: merge only if both dfs have 'uid' column ---
    if "uid" in df_combined.columns and "uid" in latest_checkup_df.columns:
        df_combined = df_combined.merge(
            latest_checkup_df, on="uid", how="left", suffixes=("", "_checkup")
        )
    else:
        # No merge possible, just proceed with employees_df
        pass

    # Normalize tanggal fields
    if "tanggal_checkup" in df_combined.columns:
        df_combined["tanggal_checkup"] = pd.to_datetime(
            df_combined["tanggal_checkup"], errors="coerce"
        ).dt.date

    if "tanggal_lahir" in df_combined.columns:
        df_combined["tanggal_lahir"] = pd.to_datetime(
            df_combined["tanggal_lahir"], errors="coerce"
        ).dt.strftime("%Y-%m-%d")

    # Fill missing medical columns to avoid KeyErrors
    medical_cols = [
        'tinggi','berat','bmi','lingkar_perut',
        'gula_darah_puasa','gula_darah_sewaktu','cholesterol','asam_urat'
    ]
    for col in medical_cols:
        if col not in df_combined.columns:
            df_combined[col] = None

    # Add status column
    df_combined['status'] = 'Well'
    df_combined.loc[
        (df_combined['gula_darah_puasa'] > 120) |
        (df_combined['gula_darah_sewaktu'] > 200) |
        (df_combined['cholesterol'] > 240) |
        (df_combined['asam_urat'] > 7) |
        (df_combined['bmi'] >= 30),
        'status'
    ] = 'Unwell'

    # Extract month/year for filtering
    if 'tanggal_checkup' in df_combined.columns:
        df_combined['bulan'] = pd.to_datetime(df_combined['tanggal_checkup'], errors='coerce').dt.month.fillna(0).astype(int)
        df_combined['tahun'] = pd.to_datetime(df_combined['tanggal_checkup'], errors='coerce').dt.year.fillna(0).astype(int)
    else:
        df_combined['bulan'] = 0
        df_combined['tahun'] = 0

    return df_combined


def get_medical_checkups_by_uid(uid: str) -> pd.DataFrame:
    """
    Fetch all medical checkups for a given employee UID.
    Returns a DataFrame filtered for that UID only.
    """
    # Use existing helper to get combined data
    df = get_dashboard_checkup_data()  # fetch all employees + latest checkup
    # Filter by UID
    if 'uid' in df.columns:
        df = df[df['uid'] == uid].copy()
    else:
        df = pd.DataFrame()
    return df



