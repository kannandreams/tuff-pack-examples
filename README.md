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

The simplified project-pack commands require Tuff 0.1.4 or newer.

The interactive demos also require Python 3.9 or newer and Claude Code.

### 2. Clone this repository

```sh
git clone https://github.com/kannandreams/tuff-pack-examples.git
cd tuff-pack-examples
```

### 3. Build the CSV pack manually

```sh
tuff pack check packs/csv-data-quality
tuff pack build packs/csv-data-quality \
  --output .work/artifacts/csv-data-quality-1.0.0.tuffpack
tuff pack verify .work/artifacts/csv-data-quality-1.0.0.tuffpack
tuff pack inspect .work/artifacts/csv-data-quality-1.0.0.tuffpack
```

This is the complete packaging workflow: the source is `packs/csv-data-quality`, and the result is a portable `.tuffpack` artifact. The source contains a skill, tool, hook, and workflow so you can inspect each one before building.

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

Inspect the exact artifact that was installed:

```sh
cd ../..
tuff pack inspect .work/artifacts/csv-data-quality-1.0.0.tuffpack
```

### 5. Run the agent (optional disposable setup)

```sh
./scripts/prepare-demo.sh csv-data-quality
cd .work/csv-data-quality
claude
```

Then ask:

```text
Inspect this project and complete the task in TASK.md. Do not disable the quality gate.
```

The starting CSV intentionally contains problems. Claude can inspect and repair it, while the installed hook prevents the task from finishing until the deterministic check passes.

To build the security-review pack manually instead:

```sh
tuff pack check packs/security-review
tuff pack build packs/security-review \
  --output .work/artifacts/security-review-1.0.0.tuffpack
tuff pack verify .work/artifacts/security-review-1.0.0.tuffpack
tuff pack inspect .work/artifacts/security-review-1.0.0.tuffpack
```

When you want to run that pack with Claude, use `./scripts/prepare-demo.sh security-review` to create a disposable consumer project. The script is a convenience for repeatable demos; it is not required to build or verify a pack.

## Package capabilities from your own agent project

You do not need to copy capabilities into a second `my-first-pack/` directory. Tuff can package capabilities it already tracks.

Assume your agent project contains `.claude/skills/code-review/SKILL.md`.

### 1. Track the existing capability

Run these commands in that agent project:

```sh
tuff init
tuff agent add claude
tuff agent set-default claude
tuff add skill .claude/skills/code-review --agent claude
tuff check
```

`tuff add` adopts the skill in place and records its accepted baseline in `tuff.lock`; it does not require you to move the file.

### 2. Build the accepted capabilities

```sh
tuff pack build --name code-review-capabilities --version 1.0.0
```

The command selects all project-scoped capabilities except the automatic Tuff CLI guide and writes:

```text
tuff-dist/code-review-capabilities-1.0.0.tuffpack
```

Choose only some capabilities with repeatable `--capability <id>` flags. Selecting a workflow automatically adds its tracked requirements.

### 3. Verify and inspect

```sh
tuff pack verify tuff-dist/code-review-capabilities-1.0.0.tuffpack
tuff pack inspect tuff-dist/code-review-capabilities-1.0.0.tuffpack
```

If the skill has unaccepted changes, the build stops and tells you to run `tuff update code-review`. No artifact is written until the project and source match the accepted baseline.

### 4. Save a reusable selection when needed

One-shot build is enough for many projects. For a pack that always contains a selected set, create an ID-based definition:

```sh
tuff pack init code-review-capabilities \
  --from-project \
  --version 1.0.0 \
  --capability code-review
tuff pack build tuff-packs/code-review-capabilities
```

The generated `tuff-packs/code-review-capabilities/tuff-pack.toml` refers to tracked IDs. It does not copy `.claude` files.

### 5. Install it into another agent project

```sh
tuff init
tuff agent add claude
tuff add pack /absolute/path/to/tuff-dist/code-review-capabilities-1.0.0.tuffpack --agent claude
tuff list
tuff check
```

For tools, hooks, workflows, standalone source-pack authoring, version updates, and common mistakes, continue with [Package your first Tuff Pack](docs/package-your-first-pack.md).

## From registries to a container image

Application images and Tuff packs travel through separate OCI lanes:

```text
application source → docker build → container image → docker push / pull ─┐
                                                                          ├→ Dockerfile COPY → agent image
tracked capabilities → tuff pack build → .tuffpack → tuff pack push / pull → extract ┘
```

For GHCR, authenticate once and publish the capability artifact with Tuff:

```sh
printf '%s' "$GHCR_TOKEN" | docker login ghcr.io --username "$GITHUB_USER" --password-stdin
tuff pack push \
  tuff-dist/code-review-capabilities-1.0.0.tuffpack \
  ghcr.io/OWNER/code-review-capabilities:1.0.0
tuff pack pull \
  ghcr.io/OWNER/code-review-capabilities:1.0.0 \
  --output build/code-review-capabilities-1.0.0.tuffpack
tuff pack extract \
  build/code-review-capabilities-1.0.0.tuffpack \
  --agent claude \
  --output build/capability-runtime
```

Docker cannot use the Tuff reference in `FROM`. Copy `build/capability-runtime` into the normal application image as shown in [Publishing and container images](docs/publishing-and-containers.md).

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
./scripts/build.sh .work/artifacts     # build both packs and keep the artifacts
./scripts/prepare-demo.sh security-review
```

`check.sh` intentionally runs each gate once against a broken fixture and once against a corrected fixture. Seeing a temporary “gate failed” message is expected; the command succeeds when it ends with `All example checks passed.`

All scripts call `tuff` from `PATH`. Set `TUFF_BIN` only when testing a particular local binary, for example `TUFF_BIN=../tuff/target/debug/tuff ./scripts/check.sh`.
