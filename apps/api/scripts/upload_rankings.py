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


def update_rankings(
    cur, school_names, school_map, df, name_col, rank_col, db_col, extra_cols=None
):
    """
    Generic ranking updater.
    extra_cols: dict of { csv_column: db_column } for additional fields to update
    """
    updated = 0
    skipped = 0

    for _, row in df.iterrows():
        uni_name = str(row[name_col]).strip()
        rank = parse_rank(str(row[rank_col]).strip())

        if not uni_name or rank is None:
            skipped += 1
            continue

        best_match = process.extractOne(uni_name, school_names)
        if best_match is None:
            skipped += 1
            continue

        match, score = best_match[:2]
        if score >= 90:
            school_id = school_map[match]

            # Build dynamic SET clause
            set_clauses = [f"{db_col} = %s"]
            values: list[int | str] = [rank]

            if extra_cols:
                for csv_col, db_column in extra_cols.items():
                    val = row.get(csv_col)
                    if pd.notna(val):
                        set_clauses.append(f"{db_column} = %s")
                        values.append(str(val).strip())

            values.append(school_id)
            sql = f"UPDATE schools SET {', '.join(set_clauses)} WHERE id = %s"
            cur.execute(sql, values)
            updated += 1
            # print(
            #     f"[success] {uni_name} ranking:{rank} (best: {match}, score: {score})"
            # )
        else:
            skipped += 1
            print(
                f"[NO MATCH] {uni_name} ranking:{rank} (best: {match}, score: {score})"
            )

    return updated, skipped


conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

cur.execute("SELECT id, name FROM schools")
schools = cur.fetchall()
school_map = {name: sid for sid, name in schools}
school_names = list(school_map.keys())
print(f"Loaded {len(school_names)} schools from DB")

# ── QS Rankings ──────────────────────────────────────────
# qs_df = pd.read_csv(Path(__file__).parent / "2026_QS_World_University_Rankings.csv")
# print(f"\nUpdating QS rankings ({len(qs_df)} universities)...")
# updated, skipped = update_rankings(
#     cur,
#     school_names,
#     school_map,
#     df=qs_df,
#     name_col="Institution Name",
#     rank_col="Rank",
#     db_col="qs_world_rank",
# )
# print(f"QS done. Updated: {updated}, Skipped: {skipped}")

# ── USNews Rankings ───────────────────────────────────────
usnews_df = pd.read_csv(Path(__file__).parent / "usnews_rankings.csv")
print(f"\nUpdating USNews rankings ({len(usnews_df)} universities)...")
updated, skipped = update_rankings(
    cur,
    school_names,
    school_map,
    df=usnews_df,
    name_col="us_news_name",
    rank_col="usnewsranking",
    db_col="usnews_global_rank",
    extra_cols={"city": "city"},  # also update city while we're here
)
print(f"USNews done. Updated: {updated}, Skipped: {skipped}")

conn.commit()
cur.close()
conn.close()
print("\nAll done.")
