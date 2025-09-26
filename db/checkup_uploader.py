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
    """
    Parse an XLS/XLSX file with employee medical checkups,
    and insert into DB. Returns a dict with inserted count and skipped rows.
    """
    all_sheets = pd.read_excel(file_path, sheet_name=None)
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

        # Convert height from meters to cm if necessary
        if 'tinggi' in df.columns:
            df['tinggi'] = df['tinggi'].apply(lambda x: x*100 if pd.notna(x) and x < 3 else x)

        # Normalize text columns
        for col in ['nama', 'jabatan']:
            if col in df.columns:
                df[col] = df[col].apply(normalize_string)

        # Handle dates
        if 'tanggal_lahir' in df.columns:
            df['tanggal_lahir'] = df['tanggal_lahir'].apply(safe_date)
        df['tanggal_checkup'] = df['tanggal_checkup'].apply(safe_date)

        # Iterate rows
        for idx, row in df.iterrows():
            if not isinstance(row, pd.Series):
                skipped.append({'row': idx+2, 'reason': 'Invalid row type'})
                continue

            row_dict = row.to_dict()

            # Skip empty rows
            if all((v is None) or (isinstance(v, float) and pd.isna(v)) or (isinstance(v, str) and not v.strip()) for v in row_dict.values()):
                skipped.append({'row': idx+2, 'reason': 'Empty row'})
                continue

            # Use UID from Excel
            uid = str(row_dict.get('uid', '')).strip()
            if not uid or not get_employee_by_uid(uid):
                skipped.append({'row': idx+2, 'reason': 'UID not found in database'})
                continue

            try:
                berat = safe_float(row_dict.get('berat'))
                tinggi_cm = safe_float(row_dict.get('tinggi'))
                tinggi_m = (tinggi_cm / 100) if tinggi_cm else None
                bmi = round(berat / (tinggi_m ** 2), 2) if berat and tinggi_m else None

                # Build checkup data WITHOUT checkup_id
                checkup_data = {
                    'uid': uid,
                    'tanggal_checkup': safe_date(row_dict.get('tanggal_checkup')) or pd.Timestamp.today().date(),
                    'tanggal_lahir': safe_date(row_dict.get('tanggal_lahir')),
                    'umur': safe_float(row_dict.get('umur')),
                    'tinggi': tinggi_cm,
                    'berat': berat,
                    'lingkar_perut': safe_float(row_dict.get('lingkar_perut')),
                    'bmi': bmi,
                    'gula_darah_puasa': safe_float(row_dict.get('gula_darah_puasa')),
                    'gula_darah_sewaktu': safe_float(row_dict.get('gula_darah_sewaktu')),
                    'cholesterol': safe_float(row_dict.get('cholesterol')),
                    'asam_urat': safe_float(row_dict.get('asam_urat')),
                    'lokasi': row_dict.get('lokasi') or sheet_name
                }

                insert_medical_checkup(**checkup_data)
                inserted += 1

            except Exception as e:
                skipped.append({'row': idx+2, 'reason': str(e)})

    return {'inserted': inserted, 'skipped': skipped}
