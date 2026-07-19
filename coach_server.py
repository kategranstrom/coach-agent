"""Custom MCP server exposing race/injury domain rules and check-in memory
to any MCP client (Claude Desktop, in particular).

Thin wrapper: all real logic lives in rules.py and memory.py as plain
functions; this file just exposes them as tools. Local Garmin activity/
wellness data is served by the separate garmin_server.py.
"""
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

import memory
import rules

# DNS-rebinding protection (default: on, allowed_origins=[]) silently 403s any
# request carrying an Origin header, including Claude Desktop's own connector
# check -- guards against a malicious website's browser hitting a local server,
# which isn't the threat model here (127.0.0.1-only, personal data, one real client).
mcp = FastMCP(
    "Coach Tools",
    port=8001,
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
)


@mcp.tool()
def get_race_context() -> dict:
    """Target race name, date, distance, and days remaining."""
    return rules.get_race_context()


@mcp.tool()
def get_injury_thresholds() -> dict:
    """Current injury thresholds (e.g. acute:chronic load ceiling). Starting points, not rigid rules."""
    return rules.get_injury_thresholds()


@mcp.tool()
def update_injury_threshold(threshold_name: str, value: float, notes: str | None = None) -> dict:
    """Adjust a threshold when the athlete says their tolerance differs from the current value."""
    return rules.update_injury_threshold(threshold_name, value, notes)


@mcp.tool()
def get_sport_impact() -> dict:
    """Sport -> knee-impact-level (high/medium/low) mapping."""
    return rules.get_sport_impact()


@mcp.tool()
def get_recent_checkins(days: int = 14) -> list[dict]:
    """The athlete's own subjective notes about how their knee/body feels, most recent first."""
    return memory.get_recent_checkins(days)


@mcp.tool()
def save_checkin(comment: str, knee_stress: int | None = None) -> dict:
    """Log a new subjective check-in (knee stress, how the athlete feels) from this conversation."""
    return memory.save_checkin(comment, knee_stress)


@mcp.tool()
def get_recent_notes(days: int = 30) -> list[dict]:
    """Past coaching notes/summaries, most recent first, to follow up on prior discussion."""
    return memory.get_recent_notes(days)


@mcp.tool()
def save_note(content: str, note_type: str = "chat_summary") -> dict:
    """Save a coaching note or summary from this conversation for future reference."""
    return memory.save_note(content, note_type)


if __name__ == "__main__":
    # --http: HTTPS for Claude Desktop's custom connectors (needs a URL, not a subprocess).
    # stdio (default): matches garmin_server.py's pattern, useful for local smoke tests.
    import sys
    if "--http" in sys.argv:
        from serve_https import serve_https
        serve_https(mcp)
    else:
        mcp.run(transport="stdio")
