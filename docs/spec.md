# Coach v2 — Consolidated Spec (post-discussion revision)

> **v3 update:** the reasoning layer described below (a custom orchestrator calling the
> Claude API directly, plus a scheduled trigger) was replaced after realizing it duplicated
> something already paid for. See "Reasoning layer" and "Trigger" below for the current
> approach: Claude Desktop's custom MCP connectors, used interactively, on an existing Pro
> subscription, instead of a separate metered API integration.

## Goals (updated from v1)
- Holistic, multi-sport coaching — not swim-race-only. Knee constraints shape *what's safe*, but improvement across any sport Garmin captures is in scope.
- Runs 1-2x/day polling Garmin for new activities (Garmin has no personal-account webhooks, so this approximates "after every activity" via frequent polling rather than true push).
- Deep training history context (full backfill + ongoing sync).
- Deep training best-practices context (RAG store) — now core, not v2.
- Displays stats + analysis after each new activity/day, not just a weekly note.
- Also a multi-turn chatbot that can answer questions and plan, grounded in full history.
- Tracks **technique**, not just load/volume — swim technique specifically, since the user can't interpret Garmin's swim metrics unaided. Matches the stated "technique-first, avoid junk mileage" philosophy that v1 never actually encoded.
- **Adaptive/personalized injury thresholds** — calibrated from the user's real flare-up history rather than generic sports-science defaults.
- **Subjective daily/activity check-ins** (knee stress + how they're feeling) — historical import from an existing Google Sheet log, plus ongoing entries collected via the chatbot going forward.
- **Backtested eval** — quantify how well the system's flags align with real historical flare-ups (e.g. "flagged 4/5 past flare-ups, average 6 days early"), not just "we have an eval set."
- **Conversational rule-tuning** — the chatbot can adjust injury/load thresholds when told to (e.g. "my knee tolerance seems lower than that").
- **Sport-mix / substitution suggestions** — given a weekly stress budget and current knee status, proactively suggest which sport combination achieves training goals.

## Architecture

### Data layer
- **Garmin MCP** (start with eddmann/garmin-connect-mcp) — full activity history across all sports + daily wellness (HR, sleep, body battery, Garmin's own training load).
- **Custom MCP server** (the differentiating piece) — race calendar, taper rules, injury thresholds (adaptive, tunable via chat), and sport knee-impact tagging (high-impact: running, hard cycling; low-impact: swimming, easy spin, most strength work).
- **RAG store** — sports-science sources on load management, taper protocols, technique benchmarks.
- **Google Sheet historical import** — one-time backfill of the existing knee-stress/feeling log. Simplest path: export the Sheet as CSV, no OAuth needed for v1 (Sheets API live-sync is a possible upgrade later, not needed since ongoing entries move to the chatbot).

### Memory (SQLite) — foundational, build early, not step 5
- `activities` — raw Garmin data, all sports
- `wellness` — daily HR/sleep/body battery/etc.
- `checkins` — date, free-text comment, knee-stress rating, linked activity; seeded from the Sheet import, appended by the ongoing check-in flow
- `analyses` — past coaching notes/flags (lets the agent reference "flagged high load last week — did it resolve?")
- `chat_history`

### Reasoning layer (v3: Claude Desktop, not a custom orchestrator)
- **No custom orchestrator script calling the Claude API directly.** That would mean paying
  for API tokens on top of an existing Claude Pro subscription, for a chat-shaped feature
  that subscription already covers.
- Instead: **`garmin_server.py` and `coach_server.py` run as local MCP servers over HTTP**
  (`--http` flag, ports 8000/8001), added to Claude Desktop as **custom connectors**
  (Settings → Connectors → name + `http://127.0.0.1:<port>/mcp`, no OAuth needed for a
  local server). Chatting with the coach means opening Desktop and talking to Claude
  directly — Claude calls the tools live, using the same subscription as any other chat.
- `rules.py` (race context, injury thresholds, sport impact) and `memory.py` (check-ins,
  past notes) are plain Python functions, wrapped as MCP tools in `coach_server.py` — same
  reasoning as before (internal logic, no external service to wrap), just now reachable by
  Desktop instead of an in-process orchestrator.
- The two servers also support stdio transport (the default, no `--http` flag) for
  scripts like `backfill_garmin.py` that spawn them as a subprocess rather than connecting
  over HTTP.

### Trigger (v3: on-demand, not scheduled)
- **No scheduled/cron trigger.** A cron job needs something to call the API on a timer,
  which is exactly the paid-API dependency this redesign avoids. There's no way to make an
  unattended background job run "for free" on a chat subscription — nothing is chatting on
  a timer.
- Instead: fully on-demand. Open Desktop, ask for an update, whenever you want one. Loses
  "proactively delivers a note without being asked," gains zero marginal cost.

### Frontend
- Streamlit: per-activity/day stats + analysis view, load/taper trend charts, chat panel. Build incrementally alongside the orchestrator rather than saving for last — you want to see results as you go.
- React/Tailwind remains a stretch goal for later polish.

### Evaluation
- Log every agent input/output for traceability.
- Backtest: run the system against historical weeks, compare its flags to the real flare-ups recorded in `checkins` (from the Sheet import), and report a concrete result.

## Build order (revised, v3)
1. ✅ SQLite memory schema.
2. ✅ Import the Google Sheet log into `checkins`.
3. ✅ Domain rules (`rules.py`): race calendar, injury thresholds, sport knee-impact tagging.
4. ✅ Garmin data: custom `garmin_server.py` (replaced the unreliable community MCP server), full history backfilled (2023-01-01 → present).
5. ✅ Check-in/note memory access (`memory.py`), wrapped with `rules.py` as MCP tools in `coach_server.py`; both servers support `--http` for Claude Desktop custom connectors.
6. Add the technique-trend signal (swim first) — expose as another `coach_server.py` tool.
7. Add sport-mix/substitution suggestions — same.
8. Adaptive thresholds, calibrated from real flare-up history (currently a generic default, explicitly labeled as such).
9. Backtested eval against historical data (`checkins` vs. what the coach actually flagged).
10. Dashboard (Streamlit) — optional at this point; the chat interface already covers the core "ask questions, get analysis" loop.

Dropped from the original plan: a custom orchestrator calling the Claude API directly, and
a scheduled/cron trigger. See "Reasoning layer" and "Trigger" above for why.

## Stack
Python, MCP Python SDK, SQLite, Claude Desktop (custom MCP connectors) for the interactive coach, Streamlit (optional, for a dashboard), CSV import for the Google Sheet.

## Honest scope note
This is now a multi-session build, not a single weekend. A realistic first sitting is steps 1-5 (plus maybe 6): memory schema, historical import, custom MCP, Garmin backfill, and one working end-to-end analysis note. Everything past that is real, valuable, and worth building — just sequenced, not simultaneous.
