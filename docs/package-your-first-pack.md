# Package your first Tuff Pack

This guide starts with an agent capability you already use as a loose file and turns it into a versioned `.tuffpack`. It then shows how to add the other capability types when you need them.

## The goal

Suppose your repository currently contains a Claude skill:

```text
your-agent-project/
  .claude/
    skills/
      code-review/
        SKILL.md
```

That file works locally, but it has no independent release identity. It is difficult to answer which version is installed in another agent, reuse exactly the same reviewed bytes, or promote it between environments.

We will create this source pack:

```text
my-first-pack/
  tuff-pack.toml
  capabilities/
    code-review/
      tuff.toml
      SKILL.md
```

and build this artifact:

```text
dist/code-review-1.0.0.tuffpack
```

## Before you begin

Install Tuff 0.1.3 or newer:

```sh
uv tool install tuffcli
tuff --version
```

If `tuff` is already managed by `uv`, use `uv tool upgrade tuffcli` for later upgrades.

## Step 1: create the portable source directory

From the directory where you want to maintain the pack source:

```sh
mkdir -p my-first-pack/capabilities/code-review
cp your-agent-project/.claude/skills/code-review/SKILL.md my-first-pack/capabilities/code-review/SKILL.md
```

The source directory is deliberately independent of `.claude`. Tuff adapters turn the same source capability into harness-native files at build or installation time.

Do not point a pack member back into the consuming agent project. Every member must be a local directory beneath the pack root so the artifact is self-contained and reproducible.

## Step 2: add the capability manifest

Create `my-first-pack/capabilities/code-review/tuff.toml`:

```toml
id = "code-review"
version = "1.0.0"
type = "skill"
description = "Review application changes for correctness and maintainability."
files = ["SKILL.md"]
```

The fields mean:

| Field | Meaning |
| --- | --- |
| `id` | Stable identity used when Tuff installs and tracks the capability. |
| `version` | Release version of this individual capability. |
| `type` | Capability primitive: `skill`, `tool`, `hook`, or `workflow`. |
| `description` | Short explanation shown in metadata and inspection output. |
| `files` | Every source file that belongs to this capability. |

The capability version and pack version are separate. They can begin together at 1.0.0 and diverge later when only one member changes.

## Step 3: add the pack manifest

Create `my-first-pack/tuff-pack.toml`:

```toml
schema = 1
name = "com.example/code-review"
version = "1.0.0"
description = "Our reviewed code-review capability."

[build]
targets = ["claude"]

[[capabilities]]
path = "capabilities/code-review"
```

`name` is the pack's stable identity. Replace `com.example` with an organization or namespace you control. `targets` tells Tuff which harness-native output to render. Each `[[capabilities]]` entry points to a directory containing a `tuff.toml`.

## Step 4: validate the source

```sh
tuff pack check my-first-pack
```

Fix every reported manifest, path, compatibility, or workflow dependency error before building. Checking does not execute packaged tools or hooks.

## Step 5: build the artifact

```sh
mkdir -p dist
tuff pack build my-first-pack --output dist/code-review-1.0.0.tuffpack
```

The output is one deterministic `.tuffpack` file. Tuff refuses unsafe source paths and does not silently overwrite an existing output file.

Use a filename containing the pack version so releases remain obvious when several artifacts are stored together.

## Step 6: verify and inspect it

```sh
tuff pack verify dist/code-review-1.0.0.tuffpack
tuff pack inspect dist/code-review-1.0.0.tuffpack
```

`verify` checks the artifact structure, metadata, and stored file digests. `inspect` prints the pack identity, members, targets, and artifact digest.

Verification proves that the artifact has not changed since it was built. It does not prove who authored or reviewed it.

## Step 7: test-install it in a clean project

Test the artifact in a clean directory before replacing the original loose capability:

```sh
mkdir pack-consumer
cd pack-consumer
tuff init
tuff agent add claude
tuff agent set-default claude
tuff add pack /absolute/path/to/dist/code-review-1.0.0.tuffpack --agent claude
tuff list
tuff check
```

Tuff verifies the complete artifact before changing the project. For this skill, it renders `.claude/skills/code-review/SKILL.md` and records the capability plus pack provenance in `tuff.lock`.

Use an absolute artifact path in the first exercise to avoid confusion about which directory relative paths are resolved from.

## Step 8: migrate the original project

The original project still contains `.claude/skills/code-review/`. Tuff will not silently overwrite that untracked directory when installing the pack.

To migrate safely:

1. confirm the loose skill is committed to version control or backed up;
2. confirm the pack contains the same reviewed files by testing the clean installation;
3. remove the original loose `.claude/skills/code-review/` directory from the consuming project;
4. run `tuff add pack /absolute/path/to/dist/code-review-1.0.0.tuffpack --agent claude` in that project;
5. run `tuff list` and `tuff check`, then review the generated files and `tuff.lock` diff.

This handoff is deliberate: refusing the collision prevents a pack installation from silently replacing user-managed agent instructions.

## Step 9: change and release it

When the skill instructions change:

1. edit the source `my-first-pack/capabilities/code-review/SKILL.md`;
2. bump the capability version in its `tuff.toml`;
3. bump the pack version in `tuff-pack.toml`;
4. check, build, verify, and inspect a new versioned output file;
5. review the diff and test the new artifact in an agent project.

Do not replace an already released `.tuffpack`. A new behavior should have a new version and digest.

## Add a tool when instructions need deterministic execution

A skill tells an agent how to reason. A tool gives it a structured executable operation. See the complete [CSV quality tool](../packs/csv-data-quality/capabilities/csv-quality-check/) for a working Python CLI and stdio MCP server.

A minimal tool source looks like:

```text
my-first-pack/capabilities/review-check/
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

Add another `[[capabilities]]` entry to `tuff-pack.toml`:

```toml
[[capabilities]]
path = "capabilities/review-check"
```

Tuff records runtime dependencies but does not install them. The destination environment must provide Python 3.9 or newer in this example.

## Add a hook when a check must run automatically

A hook connects a command to an agent lifecycle event. See the complete [CSV data-quality Stop hook](../packs/csv-data-quality/capabilities/require-data-quality/) for a working example.

```text
my-first-pack/capabilities/require-review/
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
my-first-pack/capabilities/code-review-workflow/
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

After adding the workflow to `tuff-pack.toml`, `tuff pack check` will reject the pack if a required capability is missing or has the wrong type.

## Extract instead of installing

Installation creates or updates Tuff project state. Infrastructure builds often need only the rendered harness files:

```sh
tuff pack extract dist/code-review-1.0.0.tuffpack --agent claude --output runtime-bundle
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
