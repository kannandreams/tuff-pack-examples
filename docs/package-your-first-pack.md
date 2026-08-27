# Package capabilities from an agent project

Tuff 0.1.5 can build a pack directly from capabilities already tracked in an initialized project. You do not create a separate pack folder, copy files into a packaging layout, or write `tuff-pack.toml` for a one-shot build.

## Start with the complete examples

The repository contains two initialized projects:

```text
projects/
  csv-data-quality/   # Open Agents
  security-review/    # Claude Code
```

Build either one from its project directory:

```sh
cd projects/csv-data-quality
tuff list
tuff check
tuff pack build --name csv-data-quality-capabilities --version 1.0.0
tuff pack verify tuff-dist/csv-data-quality-capabilities-1.0.0.tuffpack
tuff pack inspect tuff-dist/csv-data-quality-capabilities-1.0.0.tuffpack
```

## Convert your own project

Assume an agent project has portable capability sources under `agent-capabilities/`. This directory belongs to the application repository; it is not a pack staging directory.

```text
your-agent-project/
  agent-capabilities/
    code-review/
      tuff.toml
      SKILL.md
    review-check/
      tuff.toml
      check.py
    require-review/
      tuff.toml
      gate.py
    release-review/
      tuff.toml
  app/
```

Initialize the project and select an agent harness:

```sh
cd your-agent-project
tuff init
tuff agent add claude
tuff agent set-default claude
```

Track and render each capability:

```sh
tuff add skill agent-capabilities/code-review --agent claude
tuff add tool agent-capabilities/review-check --agent claude
tuff add hook agent-capabilities/require-review --agent claude
tuff add workflow agent-capabilities/release-review --agent claude
tuff check
```

Tuff writes the harness-native files under `.claude/`, records their source and accepted hashes in `tuff.lock`, and registers the tool and hook in Claude’s configuration. Commit the portable source, rendered harness files, `tuff.lock`, and `tuff.config.json`.

## Build from accepted project state

```sh
tuff pack build --name code-review-capabilities --version 1.0.0
```

By default, Tuff selects every project-scoped tracked capability except `tuff-cli-guide` and uses the project’s default agent. The output is:

```text
tuff-dist/code-review-capabilities-1.0.0.tuffpack
```

To select only part of a larger project, repeat `--capability`:

```sh
tuff pack build \
  --name code-review-capabilities \
  --version 1.0.0 \
  --capability release-review
```

Selecting a workflow automatically includes its tracked requirements.

## Understand the accepted-state check

Project builds do not archive arbitrary working files. Tuff checks that rendered agent files and reconstructable portable sources still match the accepted `tuff.lock` state.

When a change is intentional:

```sh
tuff diff code-review
tuff update code-review
tuff check
tuff pack build --name code-review-capabilities --version 1.0.1
```

When drift is not accepted, the build stops without writing an artifact.

## Verify, inspect, and install

```sh
tuff pack verify tuff-dist/code-review-capabilities-1.0.0.tuffpack
tuff pack inspect tuff-dist/code-review-capabilities-1.0.0.tuffpack
```

Install the release into another project:

```sh
cd ../pack-consumer
tuff init
tuff agent add claude
tuff add pack /absolute/path/to/code-review-capabilities-1.0.0.tuffpack --agent claude
tuff list
tuff check
```

Tuff verifies and stages the complete artifact before changing the consumer. Each installed member retains its capability identity and pack provenance.

## Why the source and rendered files both exist

`agent-capabilities/` is the reviewed, portable definition. `.claude/` or `.agents/` is the selected harness representation that the agent actually uses. They serve different purposes:

```text
portable source → tuff add → harness files → tuff.lock accepted state → tuff pack build
```

The separation lets a tool retain portable implementation metadata while Tuff emits the correct MCP and hook configuration for each harness. It is not a second pack layout, and users never copy these files merely to build a pack.

## Continue learning

- [CSV data-quality project](../projects/csv-data-quality/README.md)
- [Security-review project](../projects/security-review/README.md)
- [How these projects and packs work](how-the-packs-work.md)
- [Publishing and container images](publishing-and-containers.md)
