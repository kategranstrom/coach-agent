"""One-time import of the historical knee-tracker Google Sheet export into `checkins`.

The sheet has no year column, so the year is inferred by walking the rows in
order and incrementing whenever the month goes backwards (e.g. Dec -> Jan).
START_YEAR is the year of the first dated row in the export.

The source CSV contains personal medical/injury notes and is intentionally
never copied into this (public) repo -- this script reads it from wherever
it was exported to (default: Downloads) and only the script itself is committed.
"""
import csv
import sys
from pathlib import Path

from db import get_connection

MONTHS = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}

START_YEAR = 2025  # first row in the export is "May 31", which predates the Dec->Jan rollover


def parse_date(raw: str, year: int):
    parts = raw.strip().split()
    if len(parts) != 2 or parts[0] not in MONTHS:
        return None
    month = MONTHS[parts[0]]
    try:
        day = int(parts[1])
    except ValueError:
        return None
    return f"{year:04d}-{month:02d}-{day:02d}", month


def import_csv(path: Path) -> int:
    conn = get_connection()
    conn.execute("DELETE FROM checkins WHERE source = 'sheet_import'")

    year = START_YEAR
    prev_month = None
    inserted = 0

    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.reader(f):
            if len(row) < 4:
                continue
            date_raw, activity, notes = row[1], row[2], row[3]
            parsed = parse_date(date_raw, year)
            if parsed is None:
                continue
            _, month = parsed
            if prev_month is not None and month < prev_month:
                year += 1
            iso_date, month = parse_date(date_raw, year)
            prev_month = month

            activity = activity.strip()
            notes = notes.strip()
            if not activity and not notes:
                continue  # unfilled future placeholder row

            conn.execute(
                """INSERT INTO checkins (date, activity_text, comment, source)
                   VALUES (?, ?, ?, 'sheet_import')""",
                (iso_date, activity or None, notes or None),
            )
            inserted += 1

    conn.commit()
    conn.close()
    return inserted


if __name__ == "__main__":
    default_path = Path.home() / "Downloads" / "Kate's Training - Knee tracker.csv"
    csv_path = Path(sys.argv[1]) if len(sys.argv) > 1 else default_path
    count = import_csv(csv_path)
    print(f"Imported {count} check-in rows from {csv_path}")
