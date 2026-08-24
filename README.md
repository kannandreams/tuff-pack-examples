# Tuff Pack examples

This repository demonstrates why an agent's capability layer deserves its own version, independently from the application image that hosts the agent.

An application image answers **which code and runtime are deployed?** A Tuff Pack answers **which reviewed skills, tools, hooks, and workflow contract shape the agent's behaviour?** Together they give a useful production identity:

```text
agent application version + capability pack version
```

The repository contains two independently versioned packs. A team can release one without changing the other, and one application can install either or both.

| Pack | Practical scenario | Included capabilities |
| --- | --- | --- |
| [CSV data quality](packs/csv-data-quality/README.md) | A data engineer asks an agent to clean an orders CSV while a deterministic gate prevents it from finishing with invalid data. | Adapted `csv-workbench` skill, Python/MCP checker, Claude Stop hook, workflow contract |
| [Security review](packs/security-review/README.md) | A developer asks an agent to review an intentionally insecure Python service while a baseline scanner prevents obvious signals from being overlooked. | Adapted `security-review` skill, Python/MCP scanner, Claude Stop hook, workflow contract |

## Prerequisites

- Tuff CLI 0.1.3 or newer (`tuff --version`)
- Python 3.9 or newer
- Claude Code for the interactive demos
- Docker credentials only when publishing to an OCI registry

The tools use only the Python standard library. Tuff validates, packages, verifies, installs, and extracts capabilities; it does not install their runtime dependencies.

All scripts call `tuff` from `PATH` by default. Set `TUFF_BIN` to test with another binary, for example `TUFF_BIN=../tuff/target/debug/tuff ./scripts/check.sh`. This variable affects only the repository's helper scripts; it is not embedded in a pack and is not needed by the installed runtime capabilities.

## Fastest local path

```sh
./scripts/check.sh
./scripts/build.sh dist
./scripts/prepare-demo.sh csv-data-quality
cd .work/csv-data-quality
claude
```

Inside Claude, ask: `Inspect this project and complete the task in TASK.md. Do not disable the quality gate.`

Use `./scripts/prepare-demo.sh security-review` for the second example. The script refuses to overwrite an existing `.work/<demo>` directory so your work is not silently lost.

## What gets packaged

```text
pack source
  tuff-pack.toml             pack identity and members
  capabilities/
    <skill>/                 reasoning instructions
    <tool>/                  deterministic executable + MCP interface
    <hook>/                  automatic Claude Stop gate
    <workflow>/              declares which members form the workflow

build output
  <name>-1.0.0.tuffpack      immutable, deterministic artifact

installed or extracted Claude target
  .claude/skills/...
  .claude/tools/...
  .claude/hooks/...
  .claude/workflows/...
  .claude/settings.json
  .mcp.json
```

The workflow capability is a dependency contract. It tells Tuff which skill, tool, and hook must travel together and lets Tuff reject an incomplete pack. It does not run those steps in sequence. Claude follows the installed skill instructions, invokes the MCP tool, and triggers the registered hook at its native lifecycle point.

Read [How these packs work](docs/how-the-packs-work.md) for a beginner-oriented explanation of the four primitives, MCP, Stop-hook behavior, OCI, and the version boundary. Read [Adding or updating an external skill](docs/adding-or-updating-a-skill.md) for the exact `npx skills` acquisition and review process used here.

## Build, inspect, and extract

```sh
tuff pack check packs/csv-data-quality
tuff pack build packs/csv-data-quality --output dist/csv-data-quality-1.0.0.tuffpack
tuff pack verify dist/csv-data-quality-1.0.0.tuffpack
tuff pack inspect dist/csv-data-quality-1.0.0.tuffpack
tuff pack extract dist/csv-data-quality-1.0.0.tuffpack --agent claude --output dist/csv-runtime
```

Repeat with `packs/security-review`. Extraction is useful in an application-image build: pull and verify the generic OCI artifact with Tuff, extract its Claude-native filesystem tree, then `COPY` that tree into the image. A `.tuffpack` is an OCI artifact, not a Docker filesystem layer, so Docker cannot use its registry reference in `FROM`.

The executable container-context example is in [container/README.md](container/README.md).

## Publish and consume with OCI

Authenticate once using the registry's normal Docker credentials, then push an explicit version tag:

```sh
docker login ghcr.io
tuff pack push dist/csv-data-quality-1.0.0.tuffpack ghcr.io/OWNER/tuff-pack-examples:csv-data-quality-v1.0.0 --json
tuff pack pull ghcr.io/OWNER/tuff-pack-examples:csv-data-quality-v1.0.0 --output dist/downloaded.tuffpack --json
tuff pack verify dist/downloaded.tuffpack
```

Save the immutable `reference` returned by `push` and use that digest reference in deployment automation. Tags are readable release names; digests identify exact bytes. Tuff never assumes `latest` and refuses to move an existing tag unless `--force` is explicitly supplied.

The included publish workflow performs this sequence for tags named `csv-data-quality-v1.0.0` or `security-review-v1.0.0`: build, verify, authenticate, push, pull by the returned digest, compare the bytes, verify again, and extract. It becomes active after this local example is published as a GitHub repository with Packages enabled. See [Publishing and container images](docs/publishing-and-containers.md).

The workflow's `TUFF_VERSION` environment variable pins the CLI release used in CI. Update it intentionally when adopting a newer Tuff release; changing it can change validation or artifact behavior even when pack sources are unchanged.

## Versioning model

Pack versions are intentionally separate from the example application's version. If only a scanner rule changes, release `security-review` 1.0.1 without rebuilding the CSV pack. If the application code changes but its reviewed capability set does not, rebuild the application with the same digest-pinned pack.

This example starts each capability at 1.0.0 for readability. In a real team, use semantic versioning and define what counts as a breaking behavioural change before production adoption.
