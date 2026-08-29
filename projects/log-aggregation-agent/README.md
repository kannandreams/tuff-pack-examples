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

The demo walks through the complete producer-to-consumer lifecycle: source
capabilities, `tuff add`, `tuff list`, `tuff check`, pack build/verify/inspect,
GHCR publication, image listing, and a clean container that runs
`tuff pack pull`, `tuff add pack`, and the Python agent. It asks before every
step; type `n` to stop or press Enter to continue:

Install the Python dependencies with `uv` and ensure the Tuff CLI is version
0.1.5 or newer with pack support:

```sh
uv sync
```

```sh
OPENAI_API_KEY_FILE="$HOME/.config/openai/log-agent-key" \
  ./scripts/demo.sh
```

Use `./scripts/demo.sh --yes` for an unattended run. The script is only a thin
launcher; the orchestration, prompts, and formatting live in Python.

Noisy commands (`tuff add`, `tuff pack build/verify/push`, `docker build`) run
behind a spinner and collapse to a single `✓ step (1.2s)` line; their logs are
printed only when a command fails. Set `DEMO_VERBOSE=1` to stream everything.

After the push, the demo queries the GitHub Packages API and prints the real
package entry — visibility, version count, tag, digest, publish time, pull
command, and page URL. `--open-package` (or `DEMO_OPEN_PACKAGE=1`) also opens
that page in a browser.

The agent prints a condensed incident summary — lead paragraph, affected
services, coverage counts, hypotheses, and uncertainties — rather than the full
report with every evidence group and raw timeline line. Set
`AGENT_SUMMARY_FULL=1` to print `reports/agent-summary.md` verbatim.
