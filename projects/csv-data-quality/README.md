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

## Try the deterministic checker

The starting CSV intentionally contains an empty customer, a duplicate order ID, a negative amount, and a non-numeric amount:

```sh
python3 .agents/tools/csv-quality-check/server.py check
```

Exit status `1` is expected until `data/orders.csv` is corrected. The passing fixture is under `expected/orders.csv`.

## Run an agent in a sandbox

The project includes a Docker-based runtime example. It pulls the capability
pack from an OCI registry, installs the `open-agents` target into a disposable
workspace, runs the CSV repair session, and exports the repaired CSV and
quality report without modifying the host checkout.

The sample agent is a **Revenue Load Guardian**. Its job is to protect a
downstream revenue import by applying authoritative CSV corrections and
blocking completion while quality findings remain.

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
demonstration results to `demo-output/`.
