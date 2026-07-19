"""Shared field extraction for Garmin activity/wellness data.

Used by both backfill_garmin.py (to compute the typed DB columns, alongside
a full raw_json archive) and garmin_server.py's live tools (to return a lean
summary instead of the full raw payload -- an activity's complete JSON can
be tens of KB, and a wide date range of them blew past the MCP tool result
size limit (1MB) when returned unsummarized).

A few small technique fields (swim cadence/SWOLF, running cadence) are kept
alongside the core metrics since they're cheap (a handful of floats) and
directly useful for the project's technique-tracking goal; genuinely large
fields (splits, HR-zone time series, per-lap detail) are dropped -- those
stay in the DB's raw_json for later use, they just don't need to round-trip
through every tool call.
"""


def extract_activity_summary(a: dict) -> dict:
    avg_speed_mps = a.get("averageSpeed")
    return {
        "activity_id": a.get("activityId"),
        "activity_name": a.get("activityName"),
        "sport": a.get("activityType", {}).get("typeKey", "unknown"),
        "start_time": a["startTimeLocal"].replace(" ", "T") if a.get("startTimeLocal") else None,
        "duration_s": a.get("duration"),
        "distance_m": a.get("distance"),
        "avg_hr": a.get("averageHR"),
        "max_hr": a.get("maxHR"),
        "calories": a.get("calories"),
        "elevation_gain_m": a.get("elevationGain"),
        "training_load": a.get("activityTrainingLoad"),
        "avg_pace_s_per_km": (1000 / avg_speed_mps) if avg_speed_mps else None,
        "avg_swim_cadence": a.get("averageSwimCadenceInStrokesPerMinute"),
        "avg_swolf": a.get("averageSwolf"),
        "strokes": a.get("strokes"),
        "avg_running_cadence": a.get("averageRunningCadenceInStepsPerMinute"),
    }


def extract_wellness_summary(entry: dict) -> dict:
    stats = entry.get("stats") or {}
    sleep_dto = ((entry.get("sleep") or {}).get("dailySleepDTO")) or {}
    training_status = entry.get("training_status") or {}
    vo2_block = training_status.get("mostRecentVO2Max") or {}
    vo2_source = vo2_block.get("generic") or vo2_block.get("cycling")
    vo2max = vo2_source.get("vo2MaxValue") or vo2_source.get("vo2MaxPreciseValue") if isinstance(vo2_source, dict) else vo2_source
    weight_g = (entry.get("weight") or {}).get("weight")

    return {
        "date": entry.get("date"),
        "resting_hr": stats.get("restingHeartRate"),
        "sleep_score": ((sleep_dto.get("sleepScores") or {}).get("overall") or {}).get("value"),
        "sleep_duration_s": sleep_dto.get("sleepTimeSeconds"),
        "body_battery_min": stats.get("bodyBatteryLowestValue"),
        "body_battery_max": stats.get("bodyBatteryHighestValue"),
        "stress_avg": stats.get("averageStressLevel"),
        "steps": stats.get("totalSteps"),
        "weight_kg": (weight_g / 1000) if weight_g else None,
        "vo2max": vo2max,
    }
