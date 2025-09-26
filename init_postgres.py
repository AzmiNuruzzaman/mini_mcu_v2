# init_postgres.py
from sqlalchemy import create_engine, text
from config.settings import POSTGRES_URL

def init_postgres_schema():
    engine = create_engine(POSTGRES_URL)
    
    with engine.connect() as conn:
        # Create checkups table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS checkups (
                id SERIAL PRIMARY KEY,
                tanggal TIMESTAMP,
                lokasi TEXT,
                tahun INTEGER,
                nama TEXT,
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
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE,
                password TEXT,
                role TEXT
            )
        """))
        
        conn.commit()
    print("✅ PostgreSQL schema initialized successfully!")

if __name__ == "__main__":
    init_postgres_schema()