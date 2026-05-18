import json
import asyncio
import sys
from pathlib import Path

# Add parent to path so we can import database
sys.path.append(str(Path(__file__).parent.parent))

from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

from sqlalchemy import text
from database import engine


async def seed():
    json_path = Path(__file__).parent / "world_universities_and_domains.json"
    with open(json_path) as f:
        universities = json.load(f)

    print(f"Loaded {len(universities)} universities")

    async with engine.begin() as conn:
        inserted = 0
        skipped = 0

        for uni in universities:
            name = uni.get("name", "").strip()
            if not name:
                skipped += 1
                continue

            domains = uni.get("domains", [])
            web_pages = uni.get("web_pages", [])
            country = uni.get("country", "")
            alpha_two_code = uni.get("alpha_two_code", "")
            state_province = uni.get("state-province")

            await conn.execute(
                text("""
                INSERT INTO schools (
                    name, country, alpha_two_code,
                    state_province, domains, web_pages,
                    search_vector
                )
                VALUES (
                    :name, :country, :alpha_two_code,
                    :state_province, :domains, :web_pages,
                    to_tsvector('english', :name || ' ' || coalesce(:country, ''))
                )
                ON CONFLICT DO NOTHING
            """),
                {
                    "name": name,
                    "country": country,
                    "alpha_two_code": alpha_two_code,
                    "state_province": state_province,
                    "domains": domains,
                    "web_pages": web_pages,
                },
            )
            inserted += 1

            if inserted % 500 == 0:
                print(f"Inserted {inserted}...")

    print(f"Done. Inserted: {inserted}, Skipped: {skipped}")


if __name__ == "__main__":
    asyncio.run(seed())
