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
OPENAI_MODEL=gpt-5.6-terra \
OPENAI_API_KEY_FILE="$HOME/.config/openai/log-agent-key" \
python3 -m runtime.agent
```

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

## Container demo

The container uses a Compose secret for the key. This keeps the key out of
the image, environment history, prompts, and generated reports:

```sh
OPENAI_API_KEY_FILE="$HOME/.config/openai/log-agent-key" \
  ./scripts/demo.sh
```

To verify only the deterministic stage:

```sh
SKIP_AGENT=1 DEMO_STEP_DELAY=2 ./scripts/demo.sh
```

The red `$` lines are the Tuff/runtime commands being orchestrated; their
logic lives in Python rather than shell.
