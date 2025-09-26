# db/init_db.py
from db.database import get_engine
from sqlalchemy import text

def init_lokasi_table():
    """
    Ensure 'lokasi' table exists and is seeded with initial values.
    Safe to run multiple times (idempotent).
    """
    engine = get_engine()
    with engine.connect() as conn:
        # Create table if not exists
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS lokasi (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) UNIQUE NOT NULL
            );
        """))
        conn.commit()

        # Seed initial lokasi values
        seeds = [
            "Rig AB-100",
            "Rig LTO-150",
            "Rig Taylor C-200",
            "HWU EHR#10",
            "Kantor",
            "Rig Toolshop"
        ]
        for loc in seeds:
            conn.execute(
                text("""
                    INSERT INTO lokasi (name)
                    VALUES (:name)
                    ON CONFLICT (name) DO NOTHING
                """),
                {"name": loc}
            )
        conn.commit()
        print("✅ Lokasi table initialized and seeded.")


# Allow running directly with: python -m db.init_db
if __name__ == "__main__":
    init_lokasi_table()
