"""Custom Garmin Connect MCP server.

Wraps `garminconnect` directly with a single cached, persistent authenticated
client instead of re-authenticating on every tool call. The community
eddmann/garmin-connect-mcp server re-runs full login/session validation
before every single tool invocation (confirmed in its middleware.py), which
caused severe Windows port exhaustion and multi-second-per-call overhead
during bulk backfilling. Logging in once and reusing the same client cut
per-call latency from multiple seconds to ~0.1-0.3s in testing.

Reuses the same token directory created by `uvx garmin-connect-mcp auth`,
so no separate auth flow is needed.

Exposes two tools instead of replicating the community server's full 22:
- get_activities: all activities (any sport) in a date range, one call.
- get_wellness: merged daily wellness (resting HR, stress, steps, body
  battery, sleep, VO2max, weight) for a date range. Garmin has no
  single-call range endpoint for most of these, so this loops day-by-day
  internally and returns one clean merged structure per day -- callers
  don't need to know that.
"""
import json
import time
from datetime import date, timedelta
from pathlib import Path

from garminconnect import Garmin
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from garmin_extract import extract_activity_summary, extract_wellness_summary

TOKENSTORE = str(Path.home() / ".garminconnect")
DAY_CALL_DELAY = 0.15  # pacing between per-day Garmin calls -- a tight loop of ~270
                        # unpaced calls per chunk appears to trigger silent
                        # server-side throttling (a hang, not a clean error)

# DNS-rebinding protection (default: on, allowed_origins=[]) silently 403s any
# request carrying an Origin header, including Claude Desktop's own connector
# check -- guards against a malicious website's browser hitting a local server,
# which isn't the threat model here (127.0.0.1-only, personal data, one real client).
mcp = FastMCP(
    "Garmin Connect (custom)",
    port=8000,
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
)

_client: Garmin | None = None

JUNK_KEYS = {
    "userRoles",
    "ownerProfileImageUrlSmall",
    "ownerProfileImageUrlMedium",
    "ownerProfileImageUrlLarge",
    "ownerDisplayName",
}


def get_client() -> Garmin:
    global _client
    if _client is None:
        _client = Garmin()
        _client.login(TOKENSTORE)
    return _client


def _clean_activity(raw: dict) -> dict:
    return {k: v for k, v in raw.items() if k not in JUNK_KEYS}


def _daterange(start: date, end: date):
    cur = start
    while cur <= end:
        yield cur
        cur += timedelta(days=1)


@mcp.tool()
def get_activities(start_date: str, end_date: str, summary: bool = True) -> str:
    """Get activities (any sport) between start_date and end_date (YYYY-MM-DD, inclusive).

    summary=True (default) returns a lean per-activity summary (sport, duration,
    distance, HR, training load, a few technique fields) -- use this unless you
    specifically need the full raw Garmin payload, which can be large enough
    (many activities x tens of KB each) to exceed the tool result size limit
    for wide date ranges.
    """
    client = get_client()
    activities = client.get_activities_by_date(start_date, end_date)
    if summary:
        return json.dumps([extract_activity_summary(a) for a in activities])
    return json.dumps([_clean_activity(a) for a in activities])


@mcp.tool()
def get_wellness(start_date: str, end_date: str, summary: bool = True) -> str:
    """Get merged daily wellness (resting HR, stress, steps, body battery,
    sleep, VO2max, weight) for each day between start_date and end_date
    (YYYY-MM-DD, inclusive).

    summary=True (default) returns a lean per-day summary -- the full sleep
    payload alone (movement, HRV, respiration time series) is large enough
    that a multi-week range can exceed the tool result size limit unsummarized.

    sleep_score and stress_avg are Garmin's own proprietary composite scores
    (Firstbeat-derived), not something computed here -- treat them as Garmin's
    black-box model output. A day with a null sleep_score/sleep_duration_s
    means the watch recorded no sleep data at all that night (not worn/charged),
    not a parsing gap. vo2max can also legitimately go null after several weeks
    without a qualifying run/ride -- Garmin stops surfacing a stale estimate
    rather than carrying the last value forward indefinitely.
    """
    client = get_client()
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)

    weigh_ins = client.get_weigh_ins(start_date, end_date)
    weight_by_date = {}
    for w in weigh_ins.get("dailyWeightSummaries", []) or []:
        d = w.get("calendarDate") or w.get("date")
        if d:
            weight_by_date[d] = w

    days = []
    for d in _daterange(start, end):
        ds = d.isoformat()
        entry: dict = {"date": ds}
        try:
            entry["stats"] = client.get_stats(ds)
        except Exception as exc:
            entry["stats_error"] = str(exc)
        try:
            entry["sleep"] = client.get_sleep_data(ds)
        except Exception as exc:
            entry["sleep_error"] = str(exc)
        try:
            entry["training_status"] = client.get_training_status(ds)
        except Exception as exc:
            entry["training_status_error"] = str(exc)
        if ds in weight_by_date:
            entry["weight"] = weight_by_date[ds]
        days.append(entry)
        time.sleep(DAY_CALL_DELAY)

    if summary:
        return json.dumps({"days": [extract_wellness_summary(e) for e in days]})
    return json.dumps({"days": days})


if __name__ == "__main__":
    # stdio (default): used by backfill_garmin.py (spawns this as a subprocess).
    # --http: HTTPS for Claude Desktop's custom connectors (needs a URL, not a subprocess).
    import sys
    if "--http" in sys.argv:
        from serve_https import serve_https
        serve_https(mcp)
    else:
        mcp.run(transport="stdio")
