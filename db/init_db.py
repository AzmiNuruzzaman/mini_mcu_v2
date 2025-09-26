# db/init_db.py
from db.database import init_db

# ---------------------------------------------------------------------
# SCRIPT ENTRY POINT
# ---------------------------------------------------------------------
if __name__ == "__main__":
    # Initialize all tables: users, karyawan, checkups, lokasi
    init_db()
    print("✅ All tables initialized and seeded successfully!")
