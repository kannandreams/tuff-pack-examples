# Log aggregation agent

This project demonstrates a real, privacy-aware agent that compresses noisy
application logs without losing investigative context.

The agent is an **Incident Context Aggregator**. It groups repeated log lines,
preserves source line ranges and representative evidence, and asks an LLM to
write a concise incident summary from the sanitized aggregation—not from the
raw log.

## Run the deterministic engine

The deterministic engine is Python-only and requires no API key:

```sh
python3 -m log_aggregation.cli aggregate \
  --input data/api.log \
  --json-output reports/aggregation.json \
  --markdown-output reports/aggregation.md
```

It reports grouped events, compression, and complete source-line coverage.

## Run the real agent

Install dependencies, provide an API key through a file outside the project,
and run the Python agent. The model receives the deterministic MCP manifest,
not the raw log:

```sh
python3 -m pip install -r requirements.txt
OPENAI_API_KEY_FILE="$HOME/.config/openai/log-agent-key" \
python3 -m runtime.agent
```

The demo uses `gpt-5-mini` directly in `runtime/agent.py`; no model
environment variable is required.

If `reports/agent-summary.md` already exists, the agent prints the cached
summary instead of making another model request.

The key is read into memory and is never written to a prompt, report, image,
or command argument. The agent receives the deterministic aggregation and
sanitized evidence only.

## Project layout

- `log_aggregation/` — deterministic parser, grouping, sanitization, reports,
  and CLI/MCP server.
- `runtime/agent.py` — OpenAI Agents SDK runner.
- `agent-capabilities/` — Tuff skill, tool, hook, and workflow sources.
- `data/api.log` — synthetic API outage fixture.
- `reports/` — generated aggregation and agent summaries.

The Tuff pack is intentionally independent from the `csv-data-quality`
project.

## Full published-pack demo

The demo walks the complete producer-to-consumer lifecycle: source
capabilities, `tuff add`, `tuff list`, `tuff check`, pack build, verify and
inspect, GHCR publication, a runtime image build, then a clean container that
runs `tuff pack pull`, `tuff add pack`, and the Python agent.

https://github.com/user-attachments/assets/84afad2c-2951-4ddd-a490-baf0b4f51720

It asks before every step; press Enter to continue or type `n` to stop.

```sh
uv sync
OPENAI_API_KEY_FILE="$HOME/.config/openai/log-agent-key" ./scripts/demo.sh
```

Requires Tuff 0.1.5 or newer, Docker, and a `gh` login with permission to
publish to GHCR.

| Option | Effect |
| --- | --- |
| `--yes` | Approve every step; unattended run. |
| `--open-package` | Open the published GHCR package page in a browser. |
| `DEMO_VERBOSE=1` | Stream the full build logs instead of one line per step. |
| `AGENT_SUMMARY_FULL=1` | Print the complete incident report rather than the condensed summary. |
