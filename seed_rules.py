"""Seed race_calendar, injury_thresholds, and sport_impact with starting values.

Injury threshold starting value is a generic sports-science default (Gabbett's
often-cited acute:chronic workload ceiling), explicitly labeled as such --
it hasn't been calibrated against this athlete's own flare-up history yet.
That calibration is a separate, later step (correlating checkins against
load), not something to fake here.

Sport impact levels are a starting judgment call based on what actually
showed up in this athlete's own checkin comments (e.g. downhill skiing and
stairs repeatedly flagged as hard on the knee; swimming/paddling repeatedly
described as fine) -- not a generic list. Both tables are meant to be
overridden over time, not treated as ground truth.
"""
from db import get_connection

RACE = {
    "race_name": "6k Open Water Swim",
    "race_date": "2026-08-16",
    "distance_type": "open_water_swim",
    "notes": "Technique-first approach; avoid the junk-mileage pattern from last summer's ~10k/week peak.",
}

THRESHOLDS = {
    "acwr_ceiling": (1.5, "Generic sports-science default (Gabbett et al.). Not yet calibrated from this athlete's own flare-up history."),
}

# impact_level judgment grounded in this athlete's own checkin comments
# (e.g. downhill skiing/stairs repeatedly flagged as hard on the knee;
# swimming/paddling repeatedly described as fine), not a generic list.
SPORT_IMPACT = {
    "running": "high",
    "track_running": "high",
    "treadmill_running": "high",
    "resort_skiing": "high",
    "stair_climbing": "high",
    "squash": "high",
    "soccer": "high",
    "mountaineering": "high",
    "cycling": "medium",
    "indoor_cycling": "medium",
    "strength_training": "medium",
    "hiking": "medium",
    "skate_skiing_ws": "medium",
    "cross_country_skiing_ws": "medium",
    "indoor_rowing": "medium",
    "rowing_v2": "medium",
    "elliptical": "medium",
    "indoor_climbing": "medium",
    "inline_skating": "medium",
    "skating_ws": "medium",
    "multi_sport": "medium",
    "other": "medium",
    "lap_swimming": "low",
    "open_water_swimming": "low",
    "walking": "low",
    "e_bike_fitness": "low",
    "yoga": "low",
    "pilates": "low",
    "breathwork": "low",
    "stand_up_paddleboarding_v2": "low",
    "kayaking_v2": "low",
}


def seed() -> None:
    conn = get_connection()

    conn.execute("DELETE FROM race_calendar WHERE race_name = ?", (RACE["race_name"],))
    conn.execute(
        "INSERT INTO race_calendar (race_name, race_date, distance_type, notes) VALUES (?, ?, ?, ?)",
        (RACE["race_name"], RACE["race_date"], RACE["distance_type"], RACE["notes"]),
    )

    for name, (value, notes) in THRESHOLDS.items():
        conn.execute(
            """INSERT INTO injury_thresholds (threshold_name, value, notes)
               VALUES (?, ?, ?)
               ON CONFLICT(threshold_name) DO UPDATE SET
                 value=excluded.value, notes=excluded.notes, updated_at=datetime('now')""",
            (name, value, notes),
        )

    for sport, level in SPORT_IMPACT.items():
        conn.execute(
            """INSERT INTO sport_impact (sport, impact_level)
               VALUES (?, ?)
               ON CONFLICT(sport) DO UPDATE SET
                 impact_level=excluded.impact_level, updated_at=datetime('now')""",
            (sport, level),
        )

    conn.commit()
    conn.close()
    print(f"Seeded 1 race, {len(THRESHOLDS)} thresholds, {len(SPORT_IMPACT)} sport impact tags")


if __name__ == "__main__":
    seed()
