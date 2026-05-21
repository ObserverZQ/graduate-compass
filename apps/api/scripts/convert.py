import csv
import json
from pathlib import Path


# this file is for converting the json file of universities into a csv.
def to_pg_csv_array(lst):
    if not lst:
        return ""
    return ",".join(lst)


def convert():
    json_path = Path(__file__).parent / "world_universities_and_domains.json"
    with open(json_path) as f:
        universities = json.load(f)

    with open("schools.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "name",
                "country",
                "alpha_two_code",
                "state_province",
                "domains",
                "web_pages",
            ],
        )
        writer.writeheader()

        for uni in universities:
            name = uni.get("name", "").strip()
            if not name:
                continue
            writer.writerow(
                {
                    "name": name,
                    "country": uni.get("country", ""),
                    "alpha_two_code": uni.get("alpha_two_code", ""),
                    "state_province": uni.get("state-province", "") or "",
                    "domains": to_pg_csv_array(uni.get("domains", [])),
                    "web_pages": to_pg_csv_array(uni.get("web_pages", [])),
                }
            )

    print("Done — schools.csv generated")


if __name__ == "__main__":
    convert()
