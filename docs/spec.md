# Coach v2 — Consolidated Spec (post-discussion revision)

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

### Reasoning layer
- **One orchestrator agent** with tool access (Garmin MCP, custom MCP, RAG retrieval, DB) handling both:
  (a) the auto-generated per-activity/day analysis note, and
  (b) the chatbot conversation
- Reusable analysis logic rather than rigid separate agents: cross-sport load/ACWR, injury risk (incl. technique trend + knee-impact tagging), race/taper context, sport-mix suggestion.
- Split into distinct sub-agents later only if the single-prompt version starts getting confused or eval traceability demands it.

### Trigger
- Scheduled poll 1-2x/day (cron/GitHub Actions) — checks Garmin for new activity/wellness data since last sync, runs analysis, stores the note.
- Manual "check now" button in the dashboard as a fallback/demo convenience.

### Frontend
- Streamlit: per-activity/day stats + analysis view, load/taper trend charts, chat panel. Build incrementally alongside the orchestrator rather than saving for last — you want to see results as you go.
- React/Tailwind remains a stretch goal for later polish.

### Evaluation
- Log every agent input/output for traceability.
- Backtest: run the system against historical weeks, compare its flags to the real flare-ups recorded in `checkins` (from the Sheet import), and report a concrete result.

## Build order (revised)
1. SQLite memory schema — first, since everything else hangs off it.
2. Import the Google Sheet log into `checkins` (CSV export + one-time script).
3. Custom MCP server — race calendar, taper rules, injury thresholds, sport knee-impact tagging.
4. Wire up Garmin MCP; backfill ~12-18 months of activity + wellness data.
5. Single orchestrator agent with tool access to both MCPs + DB — get one real end-to-end analysis note working.
6. Add the technique-trend signal (swim first).
7. Add sport-mix/substitution suggestions.
8. Add the ongoing daily check-in flow (chatbot-prompted, writes to `checkins`).
9. Wrap the orchestrator as a multi-turn chatbot (same tools, full DB context).
10. Scheduled trigger (1-2x/day poll).
11. Adaptive thresholds, calibrated from flare-up history.
12. Conversational rule-tuning.
13. Backtested eval against historical data.
14. Dashboard — start earlier in parallel with step 5 rather than last.

## Stack
Python, MCP Python SDK, Claude API, SQLite, Streamlit, cron/GitHub Actions, CSV import for the Google Sheet.

## Honest scope note
This is now a multi-session build, not a single weekend. A realistic first sitting is steps 1-5 (plus maybe 6): memory schema, historical import, custom MCP, Garmin backfill, and one working end-to-end analysis note. Everything past that is real, valuable, and worth building — just sequenced, not simultaneous.
