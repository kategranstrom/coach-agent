"""Read/write access to check-ins and past coaching notes.

Plain functions, wrapped as MCP tools in coach_server.py -- same reasoning
as rules.py: this is internal data access, not a third-party service.
"""
from datetime import date, timedelta

from db import get_connection


def get_recent_checkins(days: int = 14) -> list[dict]:
    """Subjective check-ins (knee stress, how the athlete feels), most recent first."""
    conn = get_connection()
    since = (date.today() - timedelta(days=days)).isoformat()
    rows = conn.execute(
        """SELECT date, activity_text, knee_stress, comment, source
           FROM checkins WHERE date >= ? ORDER BY date DESC""",
        (since,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_checkin(comment: str, knee_stress: int | None = None, checkin_date: str | None = None) -> dict:
    """Log a new subjective check-in from a chat conversation."""
    conn = get_connection()
    d = checkin_date or date.today().isoformat()
    conn.execute(
        """INSERT INTO checkins (date, knee_stress, comment, source)
           VALUES (?, ?, ?, 'chatbot')""",
        (d, knee_stress, comment),
    )
    conn.commit()
    conn.close()
    return {"date": d, "knee_stress": knee_stress, "comment": comment}


def get_recent_notes(days: int = 30) -> list[dict]:
    """Past coaching notes/summaries, most recent first, to follow up on prior discussion."""
    conn = get_connection()
    since = (date.today() - timedelta(days=days)).isoformat()
    rows = conn.execute(
        """SELECT date, type, content, flags_json FROM analyses
           WHERE date >= ? ORDER BY date DESC""",
        (since,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_note(content: str, note_type: str = "chat_summary") -> dict:
    """Save a coaching note or summary from the current conversation, for future reference."""
    conn = get_connection()
    d = date.today().isoformat()
    conn.execute(
        "INSERT INTO analyses (date, type, content) VALUES (?, ?, ?)",
        (d, note_type, content),
    )
    conn.commit()
    conn.close()
    return {"date": d, "type": note_type}
