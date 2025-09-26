from sqlalchemy import create_engine, text

# temporarily hardcode your Supabase credentials
POSTGRES_URL = "postgresql://postgres.dlisqaqvedwgfldfpjls:mini_mcu_v2@aws-1-ap-southeast-1.pooler.supabase.com:5432/postgres?sslmode=require"

engine = create_engine(POSTGRES_URL)

with engine.connect() as conn:
    result = conn.execute(text("SELECT current_database(), current_user;"))
    print(result.fetchone())
