# CSV data-quality agent project

This initialized Tuff project demonstrates a data-engineering capability layer for the Open Agents (`.agents/`) format.

| Capability | Purpose |
| --- | --- |
| `csv-workbench` skill | Guides inspection, repair, validation, and reporting. |
| `csv-quality-check` tool | Produces deterministic findings through a CLI and MCP server. |
| `require-data-quality` hook | Reruns the checker before the agent finishes. |
| `csv-data-quality-review` workflow | Declares that the skill, tool, and hook travel together. |

## Build the pack

Run from this directory:

```sh
tuff list
tuff check
tuff pack build --name csv-data-quality-capabilities --version 1.0.0
tuff pack verify tuff-dist/csv-data-quality-capabilities-1.0.0.tuffpack
tuff pack inspect tuff-dist/csv-data-quality-capabilities-1.0.0.tuffpack
```

The project default is `open-agents`, so the artifact contains an Open Agents target without requiring `--agent`.

## See how it was initialized

The project already contains the result of these commands:

```sh
tuff init
tuff add skill agent-capabilities/csv-workbench --agent open-agents
tuff add tool agent-capabilities/csv-quality-check --agent open-agents
tuff add hook agent-capabilities/require-data-quality --agent open-agents
tuff add workflow agent-capabilities/csv-data-quality-review --agent open-agents
tuff check
```

The portable source stays in `agent-capabilities/`; Tuff renders the selected harness into `.agents/` and records the accepted state in `tuff.lock`. No `tuff-pack.toml` or separate pack directory is involved.

## The task

`data/orders-extract.csv` is the delivered extract and is immutable evidence.
`data/orders.csv` starts as a verbatim copy of it and is what the downstream
revenue load reads.

The extract holds three kinds of row:

| Kind | Example | Correct action |
| --- | --- | --- |
| Clean | `1001,c-1,42.50,GBP` | release |
| Repairable from the data itself | `gbp` for a known currency, whitespace, a row duplicating another in every field | repair and release |
| Missing a business fact | empty customer, `not-a-number` amount, a negative amount, a currency with no rate, two rows disagreeing on one `order_id` | quarantine with a reason |

There is no answer key. The agent is not told which rows to fix, and nothing in
the project records the expected result — the checker is the oracle.

## Try the deterministic checker

```sh
python3 .agents/tools/csv-quality-check/server.py check
```

Exit status `1` is expected until the extract has been triaged, because
`data/orders.csv` still holds the raw copy.

The checker does more than validate the released file. It reconciles row
counts against the extract, so quarantining cannot quietly become deleting:

| Shortcut | Finding |
| --- | --- |
| Drop the rows you cannot repair | `quarantine_missing` |
| Quarantine without saying why | `quarantine_reason` |
| Invent a row to keep the counts even | `invented_row` |
| Quarantine one row twice to pad the count | `quarantine_duplicate` |

## Run an agent in a sandbox

The project includes a Docker-based runtime example. It pulls the capability
pack from an OCI registry, installs the `open-agents` target into a disposable
workspace, runs the CSV repair session, and exports the repaired CSV and
quality report without modifying the host checkout.

The sample agent is a **Revenue Load Guardian**. It reads the extract and the
checker findings, then decides for each row whether the data supports a repair
or whether the missing value is a business fact it must not invent. The
before-finish hook blocks completion while findings remain.

`runtime/agent.py` runs the model through the OpenAI Agents SDK, calling the
packaged `csv_quality_check` tool over MCP. The model makes only the
repair-or-quarantine judgement; the tool decides what violates the policy, and
deterministic Python writes the files after rejecting any plan that fails to
account for every source row.

The agent step needs an OpenAI key in a file outside the project:

```sh
OPENAI_API_KEY_FILE="$HOME/.config/openai/csv-agent-key" python3 -m runtime.agent
```

See [docs/agent-runtime.md](docs/agent-runtime.md) for the local Docker
walkthrough and GitHub-hosted runner example.

For a timed, color-coded presentation of the complete local flow, run:

```sh
DEMO_STEP_DELAY=1 ./scripts/demo-agent-runtime.sh
```

The script shows the capabilities first and asks for confirmation before
rebuilding or publishing anything. Use `--yes` or `DEMO_AUTO_APPROVE=1` for a
non-interactive recording.

The script uses your existing `gh` login to publish to GitHub Container
Registry, then pulls the pack inside the sandboxed runtime. It writes only the
demonstration results to `demo-output/`, and needs `OPENAI_API_KEY_FILE` set
for the agent step.
