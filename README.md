# Tuff Pack examples

A Tuff Pack turns an agent's skills, tools, hooks, and workflows into one versioned file that you can test, publish, and install again.

If you have agent capabilities that currently live as loose files in a repository, start here. You do not need to understand OCI, MCP, or container registries to build your first pack.

## Try an example in five minutes

### 1. Install Tuff

Install the CLI once:

```sh
uv tool install tuffcli
tuff --version
```

If it is already installed with `uv`, upgrade it with:

```sh
uv tool upgrade tuffcli
```

Tuff Pack commands require Tuff 0.1.3 or newer.

The interactive demos also require Python 3.9 or newer and Claude Code.

### 2. Clone this repository

```sh
git clone https://github.com/kannandreams/tuff-pack-examples.git
cd tuff-pack-examples
```

### 3. Prepare the CSV example

```sh
./scripts/prepare-demo.sh csv-data-quality
```

The script builds the pack, creates a disposable agent project under `.work/csv-data-quality`, installs the pack for Claude, and checks the installed files.

### 4. See what was installed

```sh
cd .work/csv-data-quality
tuff list
```

You will see four capabilities:

- a skill that teaches the agent how to work with CSV data;
- a tool that performs a deterministic data-quality check;
- a hook that runs the check before Claude finishes;
- a workflow that declares that the other three capabilities belong together.

### 5. Run the agent

```sh
claude
```

Then ask:

```text
Inspect this project and complete the task in TASK.md. Do not disable the quality gate.
```

The starting CSV intentionally contains problems. Claude can inspect and repair it, while the installed hook prevents the task from finishing until the deterministic check passes.

To try the security example instead:

```sh
./scripts/prepare-demo.sh security-review
cd .work/security-review
claude
```

## Package your own capability

Start with one capability. A pack does not need to contain every capability type.

Assume you already have this Claude skill:

```text
.claude/skills/code-review/SKILL.md
```

### 1. Create a portable pack source

```text
my-first-pack/
  tuff-pack.toml
  capabilities/
    code-review/
      tuff.toml
      SKILL.md
```

Copy your existing `SKILL.md` into `my-first-pack/capabilities/code-review/`. The pack source does not use a `.claude` directory because Tuff will render the correct harness layout later.

### 2. Describe the capability

Create `my-first-pack/capabilities/code-review/tuff.toml`:

```toml
id = "code-review"
version = "1.0.0"
type = "skill"
description = "Review application changes for correctness and maintainability."
files = ["SKILL.md"]
```

### 3. Describe the pack

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

### 4. Check and build it

```sh
tuff pack check my-first-pack
mkdir -p dist
tuff pack build my-first-pack --output dist/code-review-1.0.0.tuffpack
tuff pack verify dist/code-review-1.0.0.tuffpack
tuff pack inspect dist/code-review-1.0.0.tuffpack
```

You now have a verified, versioned artifact containing your skill.

### 5. Install it into an agent project

From a different project:

```sh
tuff init
tuff agent add claude
tuff add pack /absolute/path/to/dist/code-review-1.0.0.tuffpack --agent claude
tuff list
tuff check
```

Tuff renders the skill into `.claude/skills/code-review/` and records the installed capability and pack provenance in `tuff.lock`.

For a complete walkthrough—including adding tools, hooks, workflows, version updates, and common mistakes—continue with [Package your first Tuff Pack](docs/package-your-first-pack.md).

## Explore the complete examples

| Pack | Scenario | What it demonstrates |
| --- | --- | --- |
| [CSV data quality](packs/csv-data-quality/README.md) | Repair an orders CSV before a data load | External skill, Python/MCP checker, Claude Stop hook, workflow contract |
| [Security review](packs/security-review/README.md) | Review an intentionally insecure Python service | External skill, deterministic security signals, contextual review, Claude Stop hook |

Both packs are independently versioned even though they live in one repository. A team can release one without publishing the other.

## More reading

The first guide above is enough to build and install a pack. Read these when you need the underlying details:

- [Package your first Tuff Pack](docs/package-your-first-pack.md) — the full conversion guide and optional tool, hook, and workflow templates.
- [How these packs work](docs/how-the-packs-work.md) — capability roles, deterministic builds, MCP, Claude Stop hooks, and version boundaries.
- [Adding or updating an external skill](docs/adding-or-updating-a-skill.md) — using `npx skills`, reviewing third-party content, licensing, and provenance.
- [Publishing and container images](docs/publishing-and-containers.md) — GHCR, Amazon ECR, immutable digests, promotion, and extracting a pack into an application image.
- [Container example](container/README.md) — turning an extracted Claude target into a normal Docker filesystem layer.

## Repository helper commands

These are useful after you understand the basic flow:

```sh
./scripts/check.sh                     # test both complete examples
./scripts/build.sh dist                # build both packs
./scripts/prepare-demo.sh security-review
```

`check.sh` intentionally runs each gate once against a broken fixture and once against a corrected fixture. Seeing a temporary “gate failed” message is expected; the command succeeds when it ends with `All example checks passed.`

All scripts call `tuff` from `PATH`. Set `TUFF_BIN` only when testing a particular local binary, for example `TUFF_BIN=../tuff/target/debug/tuff ./scripts/check.sh`.
