# recreate_tables.py
from sqlalchemy import create_engine, text
from config.settings import POSTGRES_URL, DEFAULT_USERS
import bcrypt

def recreate_tables():
    engine = create_engine(POSTGRES_URL)
    
    with engine.connect() as conn:
        # Drop existing tables (if any)
        conn.execute(text("DROP TABLE IF EXISTS checkups CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS users CASCADE"))
        
        # Create checkups table
        conn.execute(text("""
            CREATE TABLE checkups (
                id SERIAL PRIMARY KEY,
                tanggal TIMESTAMP,
                lokasi TEXT,
                tahun INTEGER,
                nama TEXT,
                nik TEXT,
                jabatan TEXT,
                umur INTEGER,
                tanggal_lahir TIMESTAMP,
                tinggi INTEGER,
                berat INTEGER,
                lingkar_perut INTEGER,
                bmi REAL,
                gestational_diabetes INTEGER,
                cholesterol INTEGER,
                asam_urat REAL
            )
        """))
        
        # Create users table
        conn.execute(text("""
            CREATE TABLE users (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE,
                password TEXT,
                role TEXT,
                nik TEXT
            )
        """))
        
        # Insert default users
        for username, pw, role in DEFAULT_USERS:
            hashed_pw = bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()
            conn.execute(
                text("INSERT INTO users (username, password, role, nik) VALUES (:u, :p, :r, :n)"),
                {"u": username, "p": hashed_pw, "r": role, "n": username}  # using username as default nik
    )

        
        conn.commit()
    print("✅ Tables recreated successfully!")

if __name__ == "__main__":
    recreate_tables()