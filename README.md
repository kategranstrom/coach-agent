# Coach: Autonomous Multi-Agent Training Advisor

An agentic training coach that pulls real training data from Garmin via MCP, reasons over training load, injury risk, technique, and race timing through an LLM agent with tool access, and produces grounded coaching analysis — with persistent memory of training history, subjective check-ins, and past recommendations.

## Why this project

Built as a demonstration of agentic AI system design (not a chatbot wrapper): real tool use via MCP, a custom MCP server exposing domain rules, persistent memory, and evaluation against real training history — applied to a real problem the author actually has (returning to multi-sport training around a knee injury, ahead of a 6k open-water swim on August 16).

## Goals

- Holistic, multi-sport coaching — not limited to one goal race; the tool should help improve at any sport a knee injury allows.
- Runs 1-2x/day, polling Garmin for new activity and wellness data.
- Deep context: full training history, sports-science best practices (RAG), and the athlete's own subjective notes.
- Displays stats and analysis after every new activity, and answers follow-up questions as a chatbot.
- Tracks technique trends (starting with swim), not just load and volume.
- Injury thresholds that adapt to the athlete's own flare-up history rather than generic defaults.
- Subjective daily/activity check-ins (knee stress, how it feels) — seeded from an existing personal log, extended going forward through the chatbot.
- Evaluation that backtests against real historical flare-ups and reports a concrete result, not just "we logged things."
- Conversational rule-tuning and sport-mix/substitution suggestions given current load and knee status.

## Architecture

- **Garmin MCP** — activity + wellness data across all sports.
- **Custom MCP server** — race calendar, taper rules, injury thresholds, sport knee-impact tagging. The differentiating piece: domain rules exposed as tools rather than baked into a prompt.
- **RAG store** — sports-science sources on load management, taper, and technique.
- **SQLite memory** — activities, wellness, subjective check-ins, past analyses, chat history.
- **Orchestrator agent** — one agent with tool access driving both the automated per-activity analysis and the conversational chatbot.
- **Streamlit dashboard** — trends, current status, latest analysis, and a chat panel.

See [`docs/spec.md`](docs/spec.md) for the full design writeup and build order.

## Status

Early build. See the build order in `docs/spec.md` for current progress.

## Stack

Python, MCP Python SDK, Claude API, SQLite, Streamlit, cron/GitHub Actions.
