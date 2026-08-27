# Package your first Tuff Pack

This guide starts with capabilities already used by an agent project and turns their accepted Tuff state into a versioned `.tuffpack`. It then explains tools, hooks, workflows, and the lower-level standalone source layout.

## The goal

Suppose your agent project contains a Claude skill:

```text
your-agent-project/
  .claude/
    skills/
      code-review/
        SKILL.md
```

That file works locally, but loose files have no independent release identity. We will track it in place and build this artifact without copying it:

```text
tuff-dist/code-review-capabilities-1.0.0.tuffpack
```

## Before you begin

Install Tuff 0.1.4 or newer:

```sh
uv tool install tuffcli
tuff --version
```

If `tuff` is already managed by `uv`, use `uv tool upgrade tuffcli` for later upgrades.

## Step 1: initialize and adopt the skill

Run these commands inside `your-agent-project`:

```sh
tuff init
tuff agent add claude
tuff agent set-default claude
tuff add skill .claude/skills/code-review --agent claude
tuff list
tuff check
```

Tuff recognizes the existing harness-native path, keeps the skill in place, and adds `code-review` to `tuff.lock`. The lock entry records its accepted version, installed target, and content hashes.

## Step 2: build one pack from tracked state

```sh
tuff pack build --name code-review-capabilities --version 1.0.0
```

The output is `tuff-dist/code-review-capabilities-1.0.0.tuffpack`. Tuff selects every project-scoped tracked capability except `tuff-cli-guide`, uses the project's default agent target, and refuses to overwrite an existing artifact.

To build only this skill in a project that tracks more capabilities:

```sh
tuff pack build \
  --name code-review-capabilities \
  --version 1.0.0 \
  --capability code-review \
  --agent claude
```

## Step 3: understand the accepted-state check

Project builds do not blindly archive current files. Tuff verifies that the installed capability is clean and that its reconstructable source produces the accepted lockfile baseline. If you intentionally edit `.claude/skills/code-review/SKILL.md`, accept the new baseline first:

```sh
tuff diff code-review
tuff update code-review
tuff pack build --name code-review-capabilities --version 1.0.1
```

An unaccepted change causes the build to fail without creating an artifact. This keeps “pack version 1.0.0” tied to a known project state.

## Step 4: verify and inspect

```sh
tuff pack verify tuff-dist/code-review-capabilities-1.0.0.tuffpack
tuff pack inspect tuff-dist/code-review-capabilities-1.0.0.tuffpack
```

`verify` checks the artifact structure, metadata, stored files, and whole-artifact digest. `inspect` prints the pack identity, member versions, targets, and digest. Integrity does not establish publisher trust, so consumers still review the source and publisher.

## Step 5: save the selection for repeated releases

One-shot build writes only the `.tuffpack`. If the selection itself should be reviewed and committed, create a reusable definition:

```sh
tuff pack init code-review-capabilities \
  --from-project \
  --version 1.0.0 \
  --capability code-review \
  --agent claude
```

Tuff creates `tuff-packs/code-review-capabilities/tuff-pack.toml`:

```toml
schema = 1
name = "code-review-capabilities"
version = "1.0.0"
description = "Project capability pack code-review-capabilities."

[build]
targets = ["claude"]

[project]
capabilities = ["code-review"]
```

There is no copied `capabilities/` directory. Build the definition with:

```sh
tuff pack check tuff-packs/code-review-capabilities
tuff pack build tuff-packs/code-review-capabilities
```

## Step 6: install the artifact in a clean project

```sh
mkdir pack-consumer
cd pack-consumer
tuff init
tuff agent add claude
tuff add pack /absolute/path/to/tuff-dist/code-review-capabilities-1.0.0.tuffpack --agent claude
tuff list
tuff check
```

Tuff verifies and stages the complete artifact before changing the consumer. It renders `.claude/skills/code-review/SKILL.md` and records both the individual capability identity and pack provenance in the consumer's `tuff.lock`.

## Step 7: release changes as new versions

When behavior changes, accept the capability update, build a new pack version, verify it, and test it in a clean consumer. Do not replace a released `.tuffpack`; a new behavior should have a new pack version and digest.

## Advanced: add tools, hooks, and workflows to a standalone source pack

The examples below show the lower-level `standalone-pack/capabilities/` layout. You only need this layout when the pack source is maintained separately from an initialized agent project. In a project-backed workflow, create or add the tool, hook, and workflow normally, then select their tracked IDs with `tuff pack build --name ...`.

## Add a tool when instructions need deterministic execution

A skill tells an agent how to reason. A tool gives it a structured executable operation. See the complete [CSV quality tool](../packs/csv-data-quality/capabilities/csv-quality-check/) for a working Python CLI and stdio MCP server.

A minimal tool source looks like:

```text
standalone-pack/capabilities/review-check/
  tuff.toml
  check.py
```

```toml
id = "review-check"
version = "1.0.0"
type = "tool"
description = "Run deterministic review checks."
files = ["check.py"]

[parameters]
type = "object"

[parameters.properties.path]
type = "string"
description = "Project-relative path to check."

[implementation]
language = "python3"
entrypoint = "check.py"
mcp = true
runtime_deps = ["python>=3.9"]
```

Add another `[[capabilities]]` entry to the standalone pack's `tuff-pack.toml`:

```toml
[[capabilities]]
path = "capabilities/review-check"
```

Tuff records runtime dependencies but does not install them. The destination environment must provide Python 3.9 or newer in this example.

## Add a hook when a check must run automatically

A hook connects a command to an agent lifecycle event. See the complete [CSV data-quality Stop hook](../packs/csv-data-quality/capabilities/require-data-quality/) for a working example.

```text
standalone-pack/capabilities/require-review/
  tuff.toml
  gate.py
```

```toml
id = "require-review"
version = "1.0.0"
type = "hook"
description = "Run the review check before Claude finishes."
files = ["gate.py"]

[hook]
event = "stop"
command = "python3 .claude/hooks/require-review/gate.py"
working_directory = "."
```

Add the hook directory as another pack capability. Tuff packages and registers the hook but does not execute it during build or installation. The selected agent invokes it later with the destination user's permissions, so consumers should review hook code before installing a pack.

Claude Stop hooks must handle `stop_hook_active` to avoid repeatedly blocking the same stop. Read [How these packs work](how-the-packs-work.md#claude-stop-hooks) before writing a production gate.

## Add a workflow to keep related members together

A workflow declares dependencies between capabilities. It does not orchestrate steps at runtime.

```text
standalone-pack/capabilities/code-review-workflow/
  tuff.toml
```

```toml
id = "code-review-workflow"
version = "1.0.0"
type = "workflow"
description = "Require review guidance, deterministic checks, and the Stop gate."

[[workflow.requires]]
id = "code-review"
type = "skill"

[[workflow.requires]]
id = "review-check"
type = "tool"

[[workflow.requires]]
id = "require-review"
type = "hook"
```

After adding the workflow to the standalone pack's `tuff-pack.toml`, `tuff pack check` will reject the pack if a required capability is missing or has the wrong type. For a project-backed pack, selecting the workflow automatically adds these requirements to `tuff-packs/<name>/tuff-pack.toml`.

## Extract instead of installing

Installation creates or updates Tuff project state. Infrastructure builds often need only the rendered harness files:

```sh
tuff pack extract tuff-dist/code-review-capabilities-1.0.0.tuffpack --agent claude --output runtime-bundle
```

The output directory must be missing or empty. The extracted tree can be copied into an application image or another prepared runtime. Read [Publishing and container images](publishing-and-containers.md) before using this in deployment automation.

## Common mistakes

### Starting with every primitive

Begin with the capability you already understand, usually a skill. Add a tool only when you need deterministic execution, a hook only when execution must be automatic, and a workflow only when members must travel together.

### Packaging generated harness directories

Keep portable source under the pack's `capabilities/` directory. Let Tuff produce `.claude`, `.agents`, or other harness-native output.

### Forgetting files in `files`

List every script, reference, template, and instruction file used by a capability. A build contains declared source files, not arbitrary neighboring content.

### Assuming tools run during installation

Tuff never executes member tools or hooks when checking, building, verifying, extracting, or installing a pack. Runtime execution begins only when a human, agent, hook, or CI command invokes them.

### Treating a workflow as an orchestrator

The workflow describes which capabilities belong together. The agent follows skill instructions, calls tools, and triggers native hooks; Tuff does not run the workflow as a sequence.

### Reusing an output path

Tuff refuses to overwrite existing artifacts and non-empty extraction directories. Use a new versioned artifact filename or a new empty output directory.

## Continue learning

- [CSV data-quality pack](../packs/csv-data-quality/README.md) — a complete data-engineering example.
- [Security-review pack](../packs/security-review/README.md) — a complete security example.
- [How these packs work](how-the-packs-work.md) — MCP, hooks, deterministic builds, and version identity.
- [Adding or updating an external skill](adding-or-updating-a-skill.md) — third-party skill acquisition and provenance.
- [Publishing and container images](publishing-and-containers.md) — OCI registries, digest pinning, ECR, GHCR, and Docker.
