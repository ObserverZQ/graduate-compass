import psycopg2
from dotenv import load_dotenv, find_dotenv
import os

load_dotenv(find_dotenv())

DATABASE_URL = os.getenv("DATABASE_URL", "")
DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

# Force SSL for Supabase Postgres
DATABASE_URL = DATABASE_URL + ("&" if "?" in DATABASE_URL else "?") + "sslmode=require"

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

cur.execute("INSERT INTO test (name) VALUES (%s)", ("hello from script2",))
conn.commit()

cur.close()
conn.close()
print("Row inserted successfully.")
