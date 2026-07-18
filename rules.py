"""Domain rules: race calendar, injury thresholds, sport knee-impact tags.

Plain functions, not an MCP server -- this is internal data/logic with no
external service to wrap and no need for a separate process to call it, so
the extra protocol layer wouldn't pay for itself here (unlike garmin_server.py,
which wraps a genuine third-party API). These get exposed to the orchestrator
agent as native Claude tool-use functions once that's built.

Thresholds and impact tags are starting points, not verdicts -- callers
(the agent, or you) are expected to override them as real outcomes come in.
"""
from datetime import date

from db import get_connection


def get_race_context() -> dict:
    """Race name, date, distance, and days remaining (computed from today)."""
    conn = get_connection()
    row = conn.execute(
        "SELECT race_name, race_date, distance_type, notes FROM race_calendar ORDER BY race_date LIMIT 1"
    ).fetchone()
    conn.close()
    if row is None:
        return {}
    race_date = date.fromisoformat(row["race_date"])
    return {
        "race_name": row["race_name"],
        "race_date": row["race_date"],
        "distance_type": row["distance_type"],
        "notes": row["notes"],
        "days_remaining": (race_date - date.today()).days,
    }


def get_injury_thresholds() -> dict:
    """Current injury thresholds, keyed by name, with value/notes/last-updated."""
    conn = get_connection()
    rows = conn.execute("SELECT threshold_name, value, notes, updated_at FROM injury_thresholds").fetchall()
    conn.close()
    return {
        r["threshold_name"]: {"value": r["value"], "notes": r["notes"], "updated_at": r["updated_at"]}
        for r in rows
    }


def update_injury_threshold(threshold_name: str, value: float, notes: str | None = None) -> dict:
    """Update a threshold's value (e.g. when told the athlete's tolerance differs from the current default)."""
    conn = get_connection()
    conn.execute(
        """INSERT INTO injury_thresholds (threshold_name, value, notes)
           VALUES (?, ?, ?)
           ON CONFLICT(threshold_name) DO UPDATE SET
             value=excluded.value,
             notes=COALESCE(excluded.notes, injury_thresholds.notes),
             updated_at=datetime('now')""",
        (threshold_name, value, notes),
    )
    conn.commit()
    row = conn.execute(
        "SELECT threshold_name, value, notes, updated_at FROM injury_thresholds WHERE threshold_name = ?",
        (threshold_name,),
    ).fetchone()
    conn.close()
    return dict(row)


def get_sport_impact() -> dict:
    """Sport -> knee-impact-level ('high'/'medium'/'low') mapping."""
    conn = get_connection()
    rows = conn.execute("SELECT sport, impact_level FROM sport_impact").fetchall()
    conn.close()
    return {r["sport"]: r["impact_level"] for r in rows}
