# db/excel_parser.py
# --- keep existing imports ---
import pandas as pd
import uuid
from db.queries import (
    add_employee_from_sheet as insert_karyawan_if_not_exists,
)
from db.helpers import validate_lokasi

# NEW: import checkup uploader
from db.checkup_uploader import parse_checkup_xls

# ✅ FIXED: must be dict, not set
DB_COLUMNS = {
    "nama": ["nama", "employee_name", "karyawan"],
    "jabatan": ["jabatan", "position", "title"],
    "lokasi": ["lokasi", "location", "site"],
    "tanggal_lahir": ["tanggal_lahir", "tgl_lahir", "tanggal lahir", "birthdate", "dob"],
}

MANDATORY_FIELDS_MASTER = ["nama", "jabatan", "tanggal_lahir"]

def map_columns(df):
    # keep existing map_columns
    lower_cols = {c.lower().strip(): c for c in df.columns}
    mapped = {}
    for db_col, aliases in DB_COLUMNS.items():
        for alias in aliases:
            if alias.lower().strip() in lower_cols:
                mapped[db_col] = lower_cols[alias.lower().strip()]
                break
        else:
            mapped[db_col] = None
    return mapped

def parse_master_karyawan(file_path):
    """Upload only master karyawan data, assign UID."""
    all_sheets = pd.read_excel(file_path, sheet_name=None)
    inserted, skipped = 0, 0
    batch_id = str(uuid.uuid4())

    for sheet_name, sheet_df in all_sheets.items():
        col_map = map_columns(sheet_df)
        rename_dict = {v: k for k, v in col_map.items() if v}
        sheet_df = sheet_df.rename(columns=rename_dict)

        # --- PATCH: keep only columns that exist in the sheet after renaming ---
        cols_to_keep = [mapped_col for mapped_col in col_map.keys() if mapped_col in sheet_df.columns]
        sheet_df = sheet_df[cols_to_keep]

        # Drop rows missing mandatory master fields
        sheet_df = sheet_df.dropna(
            subset=[c for c in MANDATORY_FIELDS_MASTER if c in sheet_df.columns]
        )
        sheet_df = sheet_df.where(pd.notnull(sheet_df), None)

        for _, row in sheet_df.iterrows():
            nama = str(row.get("nama")).strip()
            jabatan = str(row.get("jabatan")).strip() if row.get("jabatan") else None
            lokasi = sheet_name

            if not validate_lokasi(lokasi):
                skipped += 1
                continue

            uid = insert_karyawan_if_not_exists(
                nama=nama,
                jabatan=jabatan,
                sheet_name=lokasi,
                tanggal_lahir=row.get("tanggal_lahir"),
                batch_id=batch_id,
            )
            inserted += 1

    return {"inserted": inserted, "skipped": skipped, "batch_id": batch_id}



def parse_medical_checkup(file_path, checkup_date=None):
    """
    Upload medical checkup data.
    Now delegates to checkup_uploader.py for actual parsing & insertion.
    """
    # delegate to new uploader
    return parse_checkup_xls(file_path)
