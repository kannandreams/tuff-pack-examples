# CSV data-quality pack

This pack demonstrates a data-engineering capability layer. The application may simply host Claude Code or another Claude-compatible agent runtime; the pack contributes the reviewed behavior that teaches, measures, and enforces a particular CSV-quality practice.

| Member | Why it exists |
| --- | --- |
| `csv-workbench` skill | Teaches the agent how to inspect data, reason about assumptions, repair it responsibly, and communicate counts. |
| `csv-quality-check` tool | Produces repeatable facts from a JSON policy through CLI and MCP interfaces. |
| `require-data-quality` hook | Reruns the tool automatically when Claude tries to stop and blocks unresolved findings. |
| `csv-data-quality-review` workflow | Makes the other three capabilities an install-time dependency contract. |

The pack is version 1.0.0. Every member also has its own 1.0.0 version because Tuff tracks installed capabilities individually. These version axes can diverge later: a pack 1.1.0 could contain a checker 1.2.0 and unchanged skill 1.0.0.

## Build it manually

From the repository root:

```sh
tuff pack check packs/csv-data-quality
tuff pack build packs/csv-data-quality \
  --output .work/artifacts/csv-data-quality-1.0.0.tuffpack
tuff pack verify .work/artifacts/csv-data-quality-1.0.0.tuffpack
tuff pack inspect .work/artifacts/csv-data-quality-1.0.0.tuffpack
```

The pack source stays in this directory. Tuff reads the declared capability members and writes one portable artifact; it does not need a helper script or a second copied pack directory.

## Run it with Claude

For a disposable consumer project, use the repository helper:

```sh
./scripts/prepare-demo.sh csv-data-quality
cd .work/csv-data-quality
claude
```

Ask Claude to complete `TASK.md`. The starting CSV includes an empty customer, a duplicate order ID, a negative amount, and a non-numeric amount. The deterministic tool explains those observations; the skill guides the repair; the Stop hook prevents a premature finish.

You can inspect the same checker without an agent:

```sh
cd demos/csv-data-quality
python3 ../../packs/csv-data-quality/capabilities/csv-quality-check/server.py check
```

An exit status of 1 is expected for the intentionally broken starting fixture.
