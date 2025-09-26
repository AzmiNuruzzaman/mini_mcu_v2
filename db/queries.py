# db/queries.py
import pandas as pd
import bcrypt
import uuid
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from db.database import get_engine
import os
from config.settings import UPLOAD_DIR


# --- Expected schema for checkups table ---
CHECKUP_COLUMNS = [
    "tanggal_checkup", "tinggi", "berat", "bmi", "lingkar_perut",
    "gula_darah_puasa", "cholesterol", "asam_urat", "status",
    "tanggal_lahir", "umur", "gula_darah_sewaktu"   
]

# --- Numeric columns centralized for rounding ---
NUMERIC_COLS = [
    "tinggi", "berat", "lingkar_perut", "bmi",
    "gula_darah_puasa", "gula_darah_sewaktu",
    "cholesterol", "asam_urat"
]


# --- Utility: enforce rounding on numeric cols ---
def _round_numeric_cols(df: pd.DataFrame, cols=None, decimals=2) -> pd.DataFrame:
    if cols is None:
        cols = NUMERIC_COLS
    for col in cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).round(decimals)
    return df


# --- Karyawan ---
def get_employees():
    query = """
        SELECT uid, nama, jabatan, lokasi, tanggal_lahir
        FROM karyawan
        ORDER BY nama
    """
    return pd.read_sql(query, get_engine())

def get_employee_by_uid(uid):
    with get_engine().connect() as conn:
        result = conn.execute(
            text(
                "SELECT uid, nama, jabatan, lokasi, tanggal_lahir "
                "FROM karyawan WHERE uid = :uid"
            ),
            {"uid": uid}
        ).fetchone()
    return dict(result._mapping) if result else None

def add_employee_if_missing(nama, jabatan, lokasi, tanggal_lahir=None, batch_id=None):
    with get_engine().begin() as conn:
        existing = conn.execute(
            text(
                "SELECT uid FROM karyawan "
                "WHERE nama = :nama AND jabatan = :jabatan"
            ),
            {"nama": nama, "jabatan": jabatan}
        ).fetchone()
        if existing:
            return existing._mapping["uid"]

        new_uid = str(uuid.uuid4())
        conn.execute(
            text(
                "INSERT INTO karyawan (uid, nama, jabatan, lokasi,) "
                "VALUES (:uid, :nama, :jabatan, :lokasi,)"
            ),
            {
                "uid": new_uid,
                "nama": nama,
                "jabatan": jabatan,
                "lokasi": lokasi,
            }
        )
        return new_uid

# --- Karyawan Insert Helper (PATCH for manager XLS lokasi) ---
def add_employee_from_sheet(nama, jabatan, sheet_name, tanggal_lahir=None, batch_id=None):
    lokasi = sheet_name
    with get_engine().begin() as conn:
        existing = conn.execute(
            text(
                "SELECT uid FROM karyawan "
                "WHERE nama = :nama AND jabatan = :jabatan"
            ),
            {"nama": nama, "jabatan": jabatan}
        ).fetchone()
        if existing:
            return existing._mapping["uid"]

        new_uid = str(uuid.uuid4())
        conn.execute(
            text(
                "INSERT INTO karyawan (uid, nama, jabatan, lokasi, tanggal_lahir) "
                "VALUES (:uid, :nama, :jabatan, :lokasi, :dob)"
            ),
            {
                "uid": new_uid,
                "nama": nama,
                "jabatan": jabatan,
                "lokasi": lokasi,
                "dob": tanggal_lahir,
            }
        )
        return new_uid
    
# --- NEW: Read-only lookup for medical checkup uploads ---
def get_karyawan_uid(nama, jabatan=None, lokasi=None, tanggal_lahir=None):
    with get_engine().connect() as conn:
        query = "SELECT uid FROM karyawan WHERE nama = :nama"
        params = {"nama": nama}
        if jabatan:
            query += " AND jabatan = :jabatan"
            params["jabatan"] = jabatan
        if lokasi:
            query += " AND lokasi = :lokasi"
            params["lokasi"] = lokasi
        
        result = conn.execute(text(query), params).fetchone()
        return result._mapping["uid"] if result else None

# --- Checkups ---
def load_checkups():
    columns = [
        "c.checkup_id",
        "c.uid",
        "c.tanggal_checkup",
        "c.tanggal_lahir AS tanggal_lahir",   # take from checkups
        "c.umur",
        "c.tinggi",
        "c.berat",
        "c.lingkar_perut",
        "c.bmi",
        "c.gula_darah_puasa",
        "c.gula_darah_sewaktu",
        "c.cholesterol",
        "c.asam_urat",
        "k.nama",
        "k.jabatan",
        "k.lokasi",
    ]

    df = pd.read_sql(
        f"SELECT {', '.join(columns)} FROM checkups c JOIN karyawan k ON c.uid = k.uid ORDER BY c.tanggal_checkup DESC",
        get_engine()
    )
    df = _round_numeric_cols(df)
    for date_col in ["tanggal_checkup", "tanggal_lahir"]:
        if date_col in df.columns:
            df[date_col] = pd.to_datetime(df[date_col], errors="coerce").dt.date
    return df

def save_checkups(df: pd.DataFrame):
    """
    Save medical checkups DataFrame to DB efficiently using bulk insert.
    """
    missing_cols = [col for col in CHECKUP_COLUMNS if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")

    df = df[CHECKUP_COLUMNS].copy()
    df = _round_numeric_cols(df)

    try:
        with get_engine().begin() as conn:
            # Convert DataFrame to list of dicts for bulk insert
            records = df.to_dict(orient="records")
            if not records:
                return

            # Prepare SQL with named placeholders
            cols = ", ".join(CHECKUP_COLUMNS)
            placeholders = ", ".join([f":{c}" for c in CHECKUP_COLUMNS])
            sql = text(f"INSERT INTO checkups ({cols}) VALUES ({placeholders})")

            # Execute all rows in one go
            conn.execute(sql, records)

    except Exception as e:
        print(f"❌ Error saving checkups: {e}")
        raise e



# --- Save uploaded checkups safely ---
def save_uploaded_checkups(df: pd.DataFrame):
    """
    Save uploaded checkups from XLS file.
    Optimized for speed: batch UID lookup instead of per-row DB queries.
    """
    required_cols = [
        "nama", "jabatan", "lokasi", "tanggal_checkup",
        "tanggal_lahir", "tinggi", "berat", "lingkar_perut",
        "bmi", "gula_darah_puasa", "gula_darah_sewaktu",
        "cholesterol", "asam_urat"
    ]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")

    # Ensure dates are proper
    df["tanggal_checkup"] = pd.to_datetime(df["tanggal_checkup"], errors="coerce").dt.date
    df["tanggal_lahir"] = pd.to_datetime(df["tanggal_lahir"], errors="coerce").dt.date

    # Compute age
    today = pd.Timestamp.today().date()
    df["umur"] = df["tanggal_lahir"].apply(
        lambda d: today.year - d.year - ((today.month, today.day) < (d.month, d.day))
        if pd.notnull(d) else 0
    )

    # Round numeric columns
    df = _round_numeric_cols(df)

    # --- Batch UID mapping ---
    # Fetch all karyawan at once
    karyawan_df = pd.read_sql("SELECT uid, nama, jabatan, lokasi, tanggal_lahir FROM karyawan", get_engine())

    # Merge uploaded df with karyawan_df on multiple keys
    merged = df.merge(
        karyawan_df,
        on=["nama", "jabatan", "lokasi", "tanggal_lahir"],
        how="left",
        suffixes=("", "_karyawan")
    )

    # Keep only rows that have UID
    merged = merged[merged["uid"].notnull()].copy()

    if not merged.empty:
        # Keep CHECKUP_COLUMNS only
        merged_checkups = merged[CHECKUP_COLUMNS].copy()
        save_checkups(merged_checkups)




# --- Users ---
def get_users():
    query = "SELECT username, role FROM users"
    return pd.read_sql(query, get_engine())

def get_user_by_username(username):
    with get_engine().connect() as conn:
        result = conn.execute(
            text("SELECT username, password, role FROM users WHERE username = :username"),
            {"username": username}
        ).fetchone()
    return dict(result._mapping) if result else None

def add_user(username, password, role):
    hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode("utf-8")
    with get_engine().begin() as conn:
        conn.execute(
            text("INSERT INTO users (username, password, role) VALUES (:u, :p, :r)"),
            {"u": username, "p": hashed_pw, "r": role}
        )

def delete_user(username: str):
    with get_engine().begin() as conn:
        conn.execute(text("DELETE FROM users WHERE username = :username"), {"username": username})

def reset_user_password(username: str, new_password: str):
    hashed_pw = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode("utf-8")
    with get_engine().begin() as conn:
        conn.execute(
            text("UPDATE users SET password = :pw WHERE username = :username"),
            {"pw": hashed_pw, "username": username}
        )

def count_users_by_role(role: str) -> int:
    with get_engine().connect() as conn:
        result = conn.execute(
            text("SELECT COUNT(*) FROM users WHERE role = :role"),
            {"role": role}
        ).scalar()
    return result or 0

def get_upload_history() -> pd.DataFrame:
    """
    Return a DataFrame listing uploaded files in UPLOAD_DIR.
    Columns: filename, size_kb, created_at
    """
    records = []
    for fname in os.listdir(UPLOAD_DIR):
        path = os.path.join(UPLOAD_DIR, fname)
        if os.path.isfile(path):
            size_kb = round(os.path.getsize(path) / 1024, 2)
            created_at = pd.to_datetime(os.path.getctime(path), unit='s')
            records.append({"filename": fname, "size_kb": size_kb, "created_at": created_at})
    return pd.DataFrame(records)

#edit karyawan data
def save_manual_karyawan_edits(df: pd.DataFrame):
    """
    Persist manual edits from the manager's data editor into the 'karyawan' table.
    Expects a dataframe with 'uid' as primary key.
    """
    if df.empty:
        return 0

    engine = get_engine()
    with engine.begin() as conn:
        for _, row in df.iterrows():
            uid = row.get("uid")
            if not uid:
                continue  # skip rows without UID

            # Build the SET clause dynamically
            updates = {col: row[col] for col in row.index if col != "uid" and pd.notna(row[col])}

            if updates:
                set_clause = ", ".join([f"{col} = :{col}" for col in updates.keys()])
                sql = f"UPDATE karyawan SET {set_clause} WHERE uid = :uid"
                updates["uid"] = uid
                conn.execute(sql, updates)

    return len(df)

def reset_karyawan_data():
    """
    Delete all records from the karyawan table.
    Checkups table remains untouched.
    """
    with get_engine().begin() as conn:
        conn.execute(text("DELETE FROM karyawan"))

# --- Alias for backward compatibility ---
get_all_karyawan = get_employees

# --- Medical Checkups by UID ---
def get_medical_checkups_by_uid(uid: str) -> pd.DataFrame:
    """
    Return all medical checkup records for a given employee UID,
    ordered by checkup date descending. Column 'tanggal_checkup' is used.
    """
    query = """
        SELECT 
            checkup_id,
            uid,
            tanggal_checkup,
            tanggal_lahir,
            umur,
            tinggi,
            berat,
            lingkar_perut,
            bmi,
            gula_darah_puasa,
            gula_darah_sewaktu,
            cholesterol,
            asam_urat,
            lokasi
        FROM checkups
        WHERE uid = :uid
        ORDER BY tanggal_checkup DESC
    """
    try:
        with get_engine().connect() as conn:
            df = pd.read_sql(query, conn, params={"uid": uid})

        df = _round_numeric_cols(df)

        for date_col in ["tanggal_checkup", "tanggal_lahir"]:
            if date_col in df.columns:
                df[date_col] = pd.to_datetime(df[date_col], errors="coerce").dt.date

        return df
    except Exception as e:
        print(f"❌ Error fetching checkups for UID {uid}: {e}")
        return pd.DataFrame()



# --- Insert medical checkup with auto-rounded numeric fields ---
def insert_medical_checkup(
    uid: str,
    tanggal_checkup,
    tinggi,
    berat,
    lingkar_perut,
    bmi,
    gula_darah_puasa,
    gula_darah_sewaktu,
    cholesterol,
    asam_urat,
    tanggal_lahir=None,
    umur=None,           # ✅ keep umur (read from XLS)
    lokasi=None
):
    # Round numeric values safely
    try: tinggi = round(float(tinggi or 0), 2)
    except: tinggi = 0.0
    try: berat = round(float(berat or 0), 2)
    except: berat = 0.0
    try: lingkar_perut = round(float(lingkar_perut or 0), 2)
    except: lingkar_perut = 0.0
    try: bmi = round(float(bmi or 0), 2)
    except: bmi = 0.0
    try: gula_darah_puasa = round(float(gula_darah_puasa or 0), 2)
    except: gula_darah_puasa = 0.0
    try: gula_darah_sewaktu = round(float(gula_darah_sewaktu or 0), 2)
    except: gula_darah_sewaktu = 0.0
    try: cholesterol = round(float(cholesterol or 0), 2)
    except: cholesterol = 0.0
    try: asam_urat = round(float(asam_urat or 0), 2)
    except: asam_urat = 0.0

    # Insert into DB (do not provide checkup_id, let DB auto-generate)
    with get_engine().begin() as conn:
        sql = """
            INSERT INTO checkups (
                uid, tanggal_checkup, tinggi, berat, lingkar_perut, bmi,
                gula_darah_puasa, gula_darah_sewaktu, cholesterol, asam_urat,
                tanggal_lahir, umur, lokasi
            )
            VALUES (
                :uid, :tanggal_checkup, :tinggi, :berat, :lingkar_perut, :bmi,
                :gula_darah_puasa, :gula_darah_sewaktu, :cholesterol, :asam_urat,
                :tanggal_lahir, :umur, :lokasi
            )
        """
        conn.execute(text(sql), {
            "uid": uid,
            "tanggal_checkup": tanggal_checkup,
            "tinggi": tinggi,
            "berat": berat,
            "lingkar_perut": lingkar_perut,
            "bmi": bmi,
            "gula_darah_puasa": gula_darah_puasa,
            "gula_darah_sewaktu": gula_darah_sewaktu,
            "cholesterol": cholesterol,
            "asam_urat": asam_urat,
            "tanggal_lahir": tanggal_lahir,
            "umur": umur,
            "lokasi": lokasi
        })



# --- Optional: delete_checkup using 'begin' context ---
def delete_checkup(checkup_id: str):
    """
    Delete a checkup record by checkup_id.
    """
    with get_engine().begin() as conn:
        conn.execute(
            text("DELETE FROM checkups WHERE checkup_id = :checkup_id"),
            {"checkup_id": checkup_id}
        )


# Alias for backward compatibility
update_employee_data = save_manual_karyawan_edits

def get_latest_medical_checkup(uid: str = None) -> pd.DataFrame:
    """
    Return medical checkup records.
    If uid is provided: all checkups for that employee, ordered by checkup date descending.
    If uid is None: latest checkup for all employees.
    """
    try:
        with get_engine().connect() as conn:
            if uid:
                query = """
                    SELECT 
                        checkup_id,
                        uid,
                        tanggal_checkup,
                        tanggal_lahir,
                        umur,
                        tinggi,
                        berat,
                        lingkar_perut,
                        bmi,
                        gula_darah_puasa,
                        gula_darah_sewaktu,
                        cholesterol,
                        asam_urat,
                        lokasi
                    FROM checkups
                    WHERE uid = :uid
                    ORDER BY tanggal_checkup DESC
                """
                df = pd.read_sql(query, conn, params={"uid": uid})
            else:
                query = """
                    SELECT mc.*
                    FROM checkups mc
                    INNER JOIN (
                        SELECT uid, MAX(tanggal_checkup) AS latest_checkup
                        FROM checkups
                        GROUP BY uid
                    ) AS latest
                    ON mc.uid = latest.uid AND mc.tanggal_checkup = latest.latest_checkup
                """
                df = pd.read_sql(query, conn)

        df = _round_numeric_cols(df)

        for date_col in ["tanggal_checkup", "tanggal_lahir"]:
            if date_col in df.columns:
                df[date_col] = pd.to_datetime(df[date_col], errors="coerce").dt.date

        return df

    except Exception as e:
        print(f"❌ Error fetching checkups: {e}")
        return pd.DataFrame()
    
def delete_all_checkups():
    """
    Delete all records from the checkups table.
    """
    query = "DELETE FROM checkups"
    with get_engine().begin() as conn:
        conn.execute(text(query))






