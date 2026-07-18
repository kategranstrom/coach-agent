# Coach: Training Advisor via Custom MCP Servers + Claude Desktop

A training coach grounded in real Garmin data and personal training rules, reachable
through Claude Desktop's custom MCP connectors — chat with Claude normally and it pulls
live activity data, injury thresholds, race context, and past check-ins through two local
MCP servers this repo builds.

## Why this project

Built as a demonstration of practical MCP server design: a custom server wrapping a
third-party API reliably (after finding and fixing a real reliability bug in the community
alternative), and a second server exposing personal domain rules and memory as tools — both
usable by any MCP client, not just a bespoke chat UI. Applied to a real problem the author
has (returning to multi-sport training around a knee injury, ahead of a 6k open-water swim
on August 16).

## Goals

- Holistic, multi-sport coaching — not limited to one goal race; the tool should help improve at any sport a knee injury allows.
- Deep context: full training history (2023-present) and the athlete's own subjective notes.
- Tracks technique trends (starting with swim), not just load and volume.
- Injury thresholds that adapt to the athlete's own flare-up history rather than generic defaults — labeled honestly as a starting point, not a fabricated personalized number, until that calibration is actually built.
- Subjective daily/activity check-ins (knee stress, how it feels) — seeded from an existing personal log, extended going forward through chat.
- Conversational rule-tuning and sport-mix/substitution suggestions given current load and knee status.
- Runs through an existing Claude subscription rather than a separate metered API integration — see `docs/spec.md`'s "v3 update" for why the original scheduled-orchestrator design was dropped.

## Architecture

- **`garmin_server.py`** — custom MCP server wrapping `garminconnect` directly with a single cached, persistent session (the community MCP server re-authenticates before every tool call, which caused severe reliability problems under bulk load — see the module docstring). Serves activity + wellness data across all sports.
- **`coach_server.py`** — custom MCP server exposing race calendar, taper context, injury thresholds, sport knee-impact tags, and check-in/note memory (read + write) as tools. Plain internal logic (`rules.py`, `memory.py`), wrapped as MCP tools rather than built as a chat-specific backend.
- **SQLite (`db.py`, `schema.sql`)** — activities, wellness, subjective check-ins, injury thresholds, race calendar, sport impact, coaching notes.
- **Claude Desktop** — both servers run over `--http` locally; added as custom connectors in Desktop's settings. Chatting with the coach is just chatting with Claude, with these tools available.

See [`docs/spec.md`](docs/spec.md) for the full design writeup, including the reasoning behind dropping the original custom-orchestrator/scheduled-trigger design.

## Status

Data layer and tool servers built and tested. See the build order in `docs/spec.md` for current progress.

## Stack

Python, MCP Python SDK, SQLite, Claude Desktop (custom MCP connectors).
