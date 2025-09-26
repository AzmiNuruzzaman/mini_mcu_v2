import bcrypt
import psycopg2

# --- Connect to your backup DB ---
conn = psycopg2.connect(
    dbname="mini_mcu",        # your backup DB
    user="mini_mcu_user",     # your DB user
    password="new_password", # your DB password
    host="localhost",
    port="5432"
)
cur = conn.cursor()

# --- Fetch all users ---
cur.execute("SELECT username, password FROM users")
rows = cur.fetchall()

# --- Re-hash passwords ---
for username, plain_pw in rows:
    hashed = bcrypt.hashpw(plain_pw.encode(), bcrypt.gensalt()).decode()
    cur.execute("UPDATE users SET password=%s WHERE username=%s", (hashed, username))

conn.commit()
cur.close()
conn.close()
print("✅ All existing passwords re-hashed with bcrypt")
