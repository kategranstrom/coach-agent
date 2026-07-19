"""Backfill activities + wellness history from Garmin into the local DB.

Uses our own garmin_server.py (custom MCP server) rather than the community
eddmann/garmin-connect-mcp server. That server re-authenticates before every
single tool call (confirmed in its source), which caused severe Windows port
exhaustion and multi-second-per-call overhead once we were making hundreds of
calls for a full history backfill. Our server logs in once and reuses the
session -- calls run in ~0.1-0.3s instead.

Per-activity payloads repeat a large OAuth scope list and profile image URLs
on every single record; garmin_server.py already strips those before they
reach us.
"""
import asyncio
import json
import shutil
import sys
from datetime import date, timedelta

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from db import get_connection
from garmin_extract import extract_activity_summary, extract_wellness_summary

UV = shutil.which("uv") or "uv"
SERVER = StdioServerParameters(command=UV, args=["run", "garmin_server.py"])

START_DATE = date(2023, 1, 1)  # ~2.5 years back: pre-injury baseline + full recent history
CALL_DELAY = 0.2  # seconds between chunk calls -- polite pacing, session reuse keeps this cheap
ACTIVITIES_CHUNK_DAYS = 180
WELLNESS_CHUNK_DAYS = 30
MAX_RETRIES = 3
CALL_TIMEOUT = 240  # a chunk call should never legitimately take this long; treat as a stall


async def call_tool_json(session, name, args):
    last_exc = None
    for attempt in range(MAX_RETRIES):
        try:
            result = await asyncio.wait_for(session.call_tool(name, arguments=args), timeout=CALL_TIMEOUT)
            return json.loads(result.content[0].text)
        except (json.JSONDecodeError, asyncio.TimeoutError) as exc:
            last_exc = exc
            wait = 2 ** attempt
            print(f"  transient error calling {name} ({exc!r}, attempt {attempt + 1}/{MAX_RETRIES}), retrying in {wait}s...")
            await asyncio.sleep(wait)
    raise last_exc


def date_chunks(start: date, end: date, days: int):
    cur = start
    while cur <= end:
        chunk_end = min(cur + timedelta(days=days - 1), end)
        yield cur, chunk_end
        cur = chunk_end + timedelta(days=1)


def store_activity(conn, a: dict) -> None:
    s = extract_activity_summary(a)
    raw_json = json.dumps(a)

    conn.execute(
        """INSERT INTO activities
           (activity_id, sport, start_time, duration_s, distance_m, avg_hr, max_hr,
            calories, elevation_gain_m, training_load, avg_pace_s_per_km, raw_json, synced_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
           ON CONFLICT(activity_id) DO UPDATE SET
             sport=excluded.sport, start_time=excluded.start_time, duration_s=excluded.duration_s,
             distance_m=excluded.distance_m, avg_hr=excluded.avg_hr, max_hr=excluded.max_hr,
             calories=excluded.calories, elevation_gain_m=excluded.elevation_gain_m,
             training_load=excluded.training_load, avg_pace_s_per_km=excluded.avg_pace_s_per_km,
             raw_json=excluded.raw_json, synced_at=datetime('now')""",
        (str(s["activity_id"]), s["sport"], s["start_time"], s["duration_s"], s["distance_m"],
         s["avg_hr"], s["max_hr"], s["calories"], s["elevation_gain_m"], s["training_load"],
         s["avg_pace_s_per_km"], raw_json),
    )


async def backfill_activities(session, conn, start: date, end: date) -> None:
    print("Backfilling activities...")
    total = 0
    for chunk_start, chunk_end in date_chunks(start, end, ACTIVITIES_CHUNK_DAYS):
        try:
            activities = await call_tool_json(session, "get_activities", {
                "start_date": chunk_start.isoformat(), "end_date": chunk_end.isoformat(),
                "summary": False,  # need the full payload for the raw_json archive column
            })
        except Exception as exc:
            print(f"  WARNING: skipping activities chunk {chunk_start}..{chunk_end} due to {exc!r}")
            continue
        for a in activities:
            store_activity(conn, a)
            total += 1
        conn.commit()
        print(f"  {chunk_start}..{chunk_end}: {len(activities)} activities ({total} total so far)")
        await asyncio.sleep(CALL_DELAY)
    print(f"  {total} activities stored")


def store_wellness_day(conn, entry: dict) -> None:
    try:
        s = extract_wellness_summary(entry)
        raw_json = json.dumps({
            "stats": entry.get("stats"),
            "sleep": entry.get("sleep"),
            "training_status": entry.get("training_status"),
            "weight": entry.get("weight"),
        })

        conn.execute(
            """INSERT INTO wellness
               (date, resting_hr, sleep_score, sleep_duration_s, body_battery_min, body_battery_max,
                stress_avg, steps, weight_kg, vo2max, raw_json, synced_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
               ON CONFLICT(date) DO UPDATE SET
                 resting_hr=excluded.resting_hr, sleep_score=excluded.sleep_score,
                 sleep_duration_s=excluded.sleep_duration_s, body_battery_min=excluded.body_battery_min,
                 body_battery_max=excluded.body_battery_max, stress_avg=excluded.stress_avg,
                 steps=excluded.steps, weight_kg=excluded.weight_kg, vo2max=excluded.vo2max,
                 raw_json=excluded.raw_json, synced_at=datetime('now')""",
            (s["date"], s["resting_hr"], s["sleep_score"], s["sleep_duration_s"],
             s["body_battery_min"], s["body_battery_max"], s["stress_avg"], s["steps"],
             s["weight_kg"], s["vo2max"], raw_json),
        )
    except Exception as exc:
        print(f"  WARNING: skipping wellness day {entry.get('date')} due to {exc!r}")


async def backfill_wellness(session, conn, start: date, end: date) -> None:
    print("Backfilling wellness (stats, sleep, training status, weight)...")
    total = 0
    for chunk_start, chunk_end in date_chunks(start, end, WELLNESS_CHUNK_DAYS):
        try:
            data = await call_tool_json(session, "get_wellness", {
                "start_date": chunk_start.isoformat(), "end_date": chunk_end.isoformat(),
                "summary": False,  # need the full payload for the raw_json archive column
            })
        except Exception as exc:
            print(f"  WARNING: skipping wellness chunk {chunk_start}..{chunk_end} due to {exc!r}")
            continue
        for entry in data["days"]:
            store_wellness_day(conn, entry)
            total += 1
        conn.commit()
        print(f"  {chunk_start}..{chunk_end}: {len(data['days'])} days ({total} total so far)")
        await asyncio.sleep(CALL_DELAY)
    print(f"  {total} wellness days stored")


async def run_backfill(start: date, end: date) -> None:
    conn = get_connection()
    async with stdio_client(SERVER) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            await backfill_activities(session, conn, start, end)
            await backfill_wellness(session, conn, start, end)

    for source in ("garmin_activities", "garmin_wellness"):
        conn.execute(
            """INSERT INTO sync_state (source, last_synced_at) VALUES (?, ?)
               ON CONFLICT(source) DO UPDATE SET last_synced_at=excluded.last_synced_at""",
            (source, end.isoformat()),
        )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    start = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else START_DATE
    end = date.fromisoformat(sys.argv[2]) if len(sys.argv) > 2 else date.today()
    asyncio.run(run_backfill(start, end))
