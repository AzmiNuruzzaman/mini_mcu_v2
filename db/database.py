# db/database.py
import bcrypt
from sqlalchemy import create_engine, text
from config.settings import POSTGRES_URL, DEFAULT_USERS

# ---------------------------------------------------------------------
# CONNECTION
# ---------------------------------------------------------------------
_engine = None

def get_engine():
    """
    Return a singleton SQLAlchemy engine for Supabase PostgreSQL.
    Uses a connection pool to prevent max clients errors.
    """
    global _engine
    if _engine is None:
        # Added pool_size and max_overflow to prevent connection exhaustion during batch XLS uploads
        _engine = create_engine(
            POSTGRES_URL,
            pool_size=10,         # allow up to 10 active connections
            max_overflow=5,       # allow up to 5 extra connections temporarily
            pool_pre_ping=True,   # ensures dead connections are detected
        )
    return _engine

# ---------------------------------------------------------------------
# INITIALIZATION
# ---------------------------------------------------------------------
def init_db():
    """
    Initialize PostgreSQL schema:
    - karyawan   (from Manager XLS upload)
    - checkups   (from Nurse data entry)
    - users      (for auth, with DEFAULT_USERS bootstrapped)
    """
    engine = get_engine()
    with engine.begin() as conn:  # <-- begin() automatically commits/rollbacks
        # --- Karyawan master table ---
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS karyawan (
                uid UUID PRIMARY KEY,
                username TEXT NOT NULL,
                jabatan TEXT,
                lokasi TEXT,
                tanggal_lahir DATE
            )
        """))

        # --- Checkups table ---
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS checkups (
                checkup_id SERIAL PRIMARY KEY,
                uid UUID NOT NULL REFERENCES karyawan(uid) ON DELETE CASCADE,
                tanggal_checkup DATE NOT NULL,
                tanggal_lahir DATE,
                umur INTEGER,
                tinggi NUMERIC(5,2),
                berat NUMERIC(5,2),
                lingkar_perut NUMERIC(5,2),
                bmi NUMERIC(5,2),
                gula_darah_puasa NUMERIC(5,2),
                gula_darah_sewaktu NUMERIC(5,2),
                cholesterol NUMERIC(5,2),
                asam_urat NUMERIC(5,2),
                status VARCHAR(50)
            )
        """))

        # --- Users table ---
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(100) NOT NULL UNIQUE,
                password TEXT,
                role VARCHAR(50) NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """))

        # --- Insert default users if table is empty ---
        result = conn.execute(text("SELECT COUNT(*) FROM users")).fetchone()
        if result[0] == 0:
            for username, pw, role in DEFAULT_USERS:
                hashed_pw = bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()
                conn.execute(
                    text("INSERT INTO users (username, password, role) VALUES (:u, :p, :r)"),
                    {"u": username, "p": hashed_pw, "r": role}
                )

    print("✅ Database initialized successfully!")

# ---------------------------------------------------------------------
# SCRIPT ENTRY POINT
# ---------------------------------------------------------------------
if __name__ == "__main__":
    init_db()
