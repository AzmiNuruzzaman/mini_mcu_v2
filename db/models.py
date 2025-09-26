# db/models.py
from sqlalchemy import text
from db.database import get_engine
from config.settings import DEFAULT_USERS, INITIAL_LOKASI
import bcrypt

def recreate_tables():
    """
    Drop and recreate all main tables:
    - karyawan
    - checkups
    - users
    - lokasi
    Inserts default users from DEFAULT_USERS and seeds lokasi from INITIAL_LOKASI.
    """
    engine = get_engine()
    with engine.connect() as conn:
        # Drop tables if exist (order matters due to FK)
        conn.execute(text("DROP TABLE IF EXISTS checkups CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS karyawan CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS users CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS lokasi CASCADE"))

        # --- Recreate karyawan table ---
        conn.execute(text("""
            CREATE TABLE karyawan (
                uid UUID PRIMARY KEY,
                username TEXT NOT NULL,
                jabatan TEXT,
                lokasi TEXT,
                tanggal_lahir DATE
            )
        """))

        # --- Recreate checkups table ---
        conn.execute(text("""
            CREATE TABLE checkups (
                checkup_id SERIAL PRIMARY KEY,
                uid UUID NOT NULL REFERENCES karyawan(uid) ON DELETE CASCADE,
                tanggal DATE NOT NULL,
                tanggal_lahir DATE,
                umur INTEGER,
                tinggi NUMERIC(5,2),
                berat NUMERIC(5,2),
                lingkar_perut NUMERIC(5,2),
                bmi NUMERIC(5,2),
                gestational_diabetes NUMERIC(5,2),
                cholesterol NUMERIC(5,2),
                asam_urat NUMERIC(5,2),
                status VARCHAR(50)
            )
        """))

        # --- Recreate users table ---
        conn.execute(text("""
            CREATE TABLE users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(100) NOT NULL UNIQUE,
                password TEXT,
                role VARCHAR(50) NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """))

        # --- Recreate lokasi table ---
        conn.execute(text("""
            CREATE TABLE lokasi (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """))

        # --- Insert default users ---
        for username, pw, role in DEFAULT_USERS:
            hashed_pw = bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()
            conn.execute(
                text("INSERT INTO users (username, password, role) VALUES (:u, :p, :r)"),
                {"u": username, "p": hashed_pw, "r": role}
            )

        # --- Seed initial lokasi ---
        for loc in INITIAL_LOKASI:
            conn.execute(
                text("INSERT INTO lokasi (name) VALUES (:name) ON CONFLICT (name) DO NOTHING"),
                {"name": loc}
            )

        conn.commit()
    print("✅ Tables recreated successfully!")

# ---------------------------------------------------------------------
# SCRIPT ENTRY POINT
# ---------------------------------------------------------------------
if __name__ == "__main__":
    recreate_tables()
