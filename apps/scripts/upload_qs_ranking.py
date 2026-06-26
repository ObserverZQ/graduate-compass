import psycopg2
import pandas as pd
from thefuzz import process
from dotenv import load_dotenv, find_dotenv
import os
from pathlib import Path

load_dotenv(find_dotenv())

DATABASE_URL = os.getenv("DATABASE_URL", "")
DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
DATABASE_URL = DATABASE_URL + ("&" if "?" in DATABASE_URL else "?") + "sslmode=require"


def parse_rank(rank_str):
    if pd.isna(rank_str):
        return None
    rank_str = str(rank_str).strip().replace("=", "").replace("+", "")
    if "-" in rank_str:
        rank_str = rank_str.split("-")[0]
    try:
        return int(rank_str)
    except:
        return None


# Load QS CSV
df = pd.read_csv(Path(__file__).parent / "2026_QS_World_University_Rankings.csv")
# df = pd.read_csv("2026_QS_World_University_Rankings.csv")

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

# Get all schools from DB
cur.execute("SELECT id, name FROM schools")
schools = cur.fetchall()
school_map = {name: sid for sid, name in schools}
school_names = list(school_map.keys())

print(f"Loaded {len(school_names)} schools from DB")
print(f"Loaded {len(df)} QS ranked universities")

updated = 0
skipped = 0

for _, row in df.iterrows():
    qs_name = str(row["Institution Name"]).strip()
    qs_rank = parse_rank(str(row["Rank"]).strip())

    if not qs_name or qs_rank is None:
        skipped += 1
        continue

    best_match = process.extractOne(qs_name, school_names)

    if best_match is None:
        skipped += 1
        print(f"[NO MATCH] {qs_name} (no choices available)")
        continue

    # if qs_name == "University of Oxford":
    #     print(f"best_match: {best_match}, {best_match[:2]}")

    match, score = best_match[:2]
    if score >= 80:
        # if qs_name == "University of Oxford":
        #     school_id = school_map[match]
        #     print(f"best_match: {school_id}, {best_match[:2]}, {qs_rank}")
        #     cur.execute(
        #         "UPDATE schools SET qs_world_rank = %s WHERE id = %s",
        #         (qs_rank, school_id),
        #     )
        school_id = school_map[match]
        cur.execute(
            "UPDATE schools SET qs_world_rank = %s WHERE id = %s", (qs_rank, school_id)
        )
        updated += 1
        # print(f"[{score}] {qs_name} → {match} | rank: {qs_rank} | id: {school_id}")
    else:
        skipped += 1
        print(f"[NO MATCH] {qs_name} (best: {match}, score: {score})")

conn.commit()
cur.close()
conn.close()
print(f"\nDone. Updated: {updated}, Skipped: {skipped}")
