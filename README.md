# Tuff Pack examples

This repository contains three real agent projects whose capabilities are initialized, tracked, and ready to package with Tuff. There is no separate pack source directory and no helper script hiding the build.

| Project | Agent layout | Capability set |
| --- | --- | --- |
| [CSV data quality](projects/csv-data-quality/README.md) | Open Agents (`.agents/`) | Skill, Python/MCP checker, before-finish hook, workflow |
| [Security review](projects/security-review/README.md) | Claude Code (`.claude/`) | Skill, Python/MCP scanner, Stop hook, workflow |
| [Log aggregation](projects/log-aggregation-agent/README.md) | Open Agents (`.agents/`) | Skill, Python/MCP aggregator, before-finish hook, workflow |

## Install Tuff

These examples require Tuff 0.1.5 or newer:

```sh
uv tool install tuffcli
tuff --version
```

If Tuff is already installed with `uv`, upgrade it with `uv tool upgrade tuffcli`.

## Example 1: build the Open Agents data-quality pack

```sh
git clone https://github.com/kannandreams/tuff-pack-examples.git
cd tuff-pack-examples/projects/csv-data-quality
```

This is already an initialized Tuff project. Inspect its tracked state:

```sh
tuff list
tuff check
```

Build the accepted capabilities directly from `tuff.lock`:

```sh
tuff pack build \
  --name csv-data-quality-capabilities \
  --version 1.0.0
```

Tuff writes `tuff-dist/csv-data-quality-capabilities-1.0.0.tuffpack`. Verify and inspect it:

```sh
tuff pack verify tuff-dist/csv-data-quality-capabilities-1.0.0.tuffpack
tuff pack inspect tuff-dist/csv-data-quality-capabilities-1.0.0.tuffpack
```

The inspected target is `open-agents`, and the pack contains all four tracked project capabilities. Tuff excludes its built-in `tuff-cli-guide` automatically.

## Example 2: build the Claude security-review pack

```sh
cd ../security-review
tuff list
tuff check
tuff pack build \
  --name security-review-capabilities \
  --version 1.0.0
tuff pack verify tuff-dist/security-review-capabilities-1.0.0.tuffpack
tuff pack inspect tuff-dist/security-review-capabilities-1.0.0.tuffpack
```

The inspected target is `claude`. The project includes application code with intentional security findings so the scanner, skill, and Stop hook have a concrete task to perform.

## What is happening

Each project has four layers:

```text
agent-capabilities/       reviewed portable source for skills, tools, hooks, workflows
        │ tuff add
        ▼
.agents/ or .claude/     files rendered for the selected agent harness
        │ accepted state recorded by Tuff
        ▼
tuff.lock                exact capability identities, targets, and content hashes
        │ tuff pack build --name ...
        ▼
tuff-dist/*.tuffpack     versioned capability release artifact
```

`agent-capabilities/` belongs to the agent project. It is not a copied pack directory. The pack build reads the already tracked project state and creates its temporary packaging structure internally.

## How the projects were initialized

The committed projects are ready to build, so you do not need to rerun these commands. They are shown to make the setup reproducible in your own repository.

CSV data quality used Open Agents:

```sh
tuff init
tuff add skill agent-capabilities/csv-workbench --agent open-agents
tuff add tool agent-capabilities/csv-quality-check --agent open-agents
tuff add hook agent-capabilities/require-data-quality --agent open-agents
tuff add workflow agent-capabilities/csv-data-quality-review --agent open-agents
tuff check
```

Security review used Claude:

```sh
tuff init
tuff agent add claude
tuff agent set-default claude
tuff add skill agent-capabilities/security-review --agent claude
tuff add tool agent-capabilities/security-baseline-scan --agent claude
tuff add hook agent-capabilities/require-security-review --agent claude
tuff add workflow agent-capabilities/secure-release-review --agent claude
tuff check
```

Commit `tuff.lock`, `tuff.config.json`, the portable sources, and the rendered agent files. When you intentionally change a tracked capability, inspect and accept the new baseline before releasing another pack version:

```sh
tuff diff csv-workbench
tuff update csv-workbench
tuff pack build --name csv-data-quality-capabilities --version 1.0.1
```

## Publish and consume

After building, a pack supports the full delivery flow:

```text
build → verify → push → pull → extract
```

For example:

```sh
tuff pack push \
  tuff-dist/security-review-capabilities-1.0.0.tuffpack \
  ghcr.io/OWNER/security-review-capabilities:1.0.0
tuff pack pull \
  ghcr.io/OWNER/security-review-capabilities:1.0.0 \
  --output pulled.tuffpack
tuff pack extract pulled.tuffpack --agent claude --output capability-runtime
```

Use your lowercase GitHub owner in the GHCR reference. If Docker reports a missing `docker-credential-desktop` helper, see the [temporary Docker config login](docs/publishing-and-containers.md#ghcr-release) before running `tuff pack push`.

Read [Publishing and container images](docs/publishing-and-containers.md) for GHCR, Amazon ECR, immutable digests, and Docker image integration.

## More reading

- [Package your first Tuff Pack](docs/package-your-first-pack.md)
- [How these projects and packs work](docs/how-the-packs-work.md)
- [Adding or updating an external skill](docs/adding-or-updating-a-skill.md)
- [Container example](container/README.md)

## Repository checks

The scripts are for maintainers and CI; users do not need them to build either example:

```sh
./scripts/check.sh
./scripts/build.sh .work/artifacts
```

All scripts call `tuff` from `PATH`. Set `TUFF_BIN` only when testing a local binary.
