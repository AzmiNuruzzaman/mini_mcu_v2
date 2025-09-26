# db/checkup_uploader.py
import pandas as pd
from db.queries import get_employee_by_uid, insert_medical_checkup
from datetime import datetime

# -----------------------------
# Helper functions
# -----------------------------
def normalize_string(val):
    if isinstance(val, str):
        return val.strip().lower()
    elif pd.notna(val):
        return str(val).strip().lower()
    return ''

def safe_float(val):
    try:
        if pd.notna(val):
            return float(val)
    except:
        pass
    return None

def safe_date(val):
    try:
        dt = pd.to_datetime(val).date()
        if dt.year < 1901:
            return None
        return dt
    except:
        return None

# -----------------------------
# Main parser and uploader
# -----------------------------
def parse_checkup_xls(file_path):
    all_sheets = pd.read_excel(file_path, sheet_name=None, dtype=str)  # read all as str to clean easily
    inserted = 0
    skipped = []

    for sheet_name, df in all_sheets.items():
        # Normalize columns
        df.columns = [c.strip().lower().replace(' ', '_') for c in df.columns]

        # Fill missing 'lokasi' with sheet name
        if 'lokasi' not in df.columns or df['lokasi'].isnull().all():
            df['lokasi'] = sheet_name

        # Fill missing 'tanggal_checkup' with today
        if 'tanggal_checkup' not in df.columns:
            df['tanggal_checkup'] = pd.Timestamp.today().date()

        # Clean UID
        df['uid'] = df['uid'].astype(str).str.strip()
        df = df[df['uid'].notna() & (df['uid'] != 'nan')]

        # Convert text columns
        for col in ['nama', 'jabatan', 'lokasi']:
            if col in df.columns:
                df[col] = df[col].apply(normalize_string)

        # Convert numeric fields
        numeric_cols = ['tinggi','berat','lingkar_perut','gula_darah_puasa','gula_darah_sewaktu','cholesterol','asam_urat','umur','bmi']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = df[col].str.replace(',', '.').apply(safe_float)

        # Convert dates
        for col in ['tanggal_lahir', 'tanggal_checkup']:
            if col in df.columns:
                df[col] = df[col].apply(lambda x: safe_date(pd.to_datetime(x, dayfirst=True, errors='coerce')))

        # Iterate rows
        for idx, row in df.iterrows():
            row_dict = row.to_dict()
            uid = row_dict.get('uid')
            if not uid or not get_employee_by_uid(uid):
                skipped.append({'row': idx+2, 'reason': 'UID not found in database'})
                continue

            try:
                tinggi_cm = row_dict.get('tinggi')
                berat = row_dict.get('berat')
                tinggi_m = (tinggi_cm / 100) if tinggi_cm else None
                bmi = round(berat / (tinggi_m ** 2), 2) if berat and tinggi_m else row_dict.get('bmi')

                checkup_data = {
                    'uid': uid,
                    'tanggal_checkup': row_dict.get('tanggal_checkup') or pd.Timestamp.today().date(),
                    'tanggal_lahir': row_dict.get('tanggal_lahir'),
                    'umur': row_dict.get('umur'),
                    'tinggi': tinggi_cm,
                    'berat': berat,
                    'lingkar_perut': row_dict.get('lingkar_perut'),
                    'bmi': bmi,
                    'gula_darah_puasa': row_dict.get('gula_darah_puasa'),
                    'gula_darah_sewaktu': row_dict.get('gula_darah_sewaktu'),
                    'cholesterol': row_dict.get('cholesterol'),
                    'asam_urat': row_dict.get('asam_urat'),
                    'lokasi': row_dict.get('lokasi') or sheet_name
                }
                insert_medical_checkup(**checkup_data)
                inserted += 1
            except Exception as e:
                skipped.append({'row': idx+2, 'reason': str(e)})

    return {'inserted': inserted, 'skipped': skipped}

