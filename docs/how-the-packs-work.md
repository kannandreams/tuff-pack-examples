# How these packs work

## Why one repository can contain multiple packs

A repository is a source-control boundary; a pack is a release boundary. They do not have to be one-to-one. This repository keeps related examples together while each `tuff-pack.toml` gives its pack an independent name, version, membership list, and build target.

That means a CSV capability change can release `csv-data-quality-v1.0.1` without changing or republishing `security-review` 1.0.0. Consumers choose a pack reference, not the whole Git repository. Keeping multiple packs together is useful when they share maintainers, tests, and release policy. Separate repositories may be better when ownership or access control differs.

## Four capability primitives

The CSV example illustrates the separation of concerns:

```text
user task
   |
   v
skill: how the agent should reason and communicate
   |
   v
tool: reproducible measurements available through MCP
   |
   v
agent edits project files
   |
   v
hook: reruns the measurement at Claude's Stop event
   |
   +-- pass --> Claude may stop
   |
   +-- fail --> exit 2 feedback asks Claude to continue

workflow: declares that skill + tool + hook must be packaged together
```

The security example uses the same shape but preserves an important distinction: the tool finds pattern signals, while the skill performs contextual security reasoning. A baseline scanner cannot establish exploitability and a clean scan cannot prove security.

## What Tuff does at each stage

`tuff pack check` validates manifests, target support, workflow requirements, paths, and member compatibility. It does not run packaged code.

`tuff pack build` creates a deterministic `.tuffpack` containing member sources and pre-rendered Claude output. The same source bytes should produce the same pack digest; `scripts/check.sh` builds every pack twice and compares the bytes.

`tuff pack verify` validates the artifact structure, canonical metadata, file digests, and overall artifact digest.

`tuff pack push` puts those exact bytes into a generic OCI artifact. Authentication comes from `docker login` or `podman login`. Tuff returns the artifact digest and an immutable OCI manifest digest reference.

`tuff pack pull` downloads by tag or digest, validates the OCI descriptors and Tuff artifact, and writes atomically without overwriting an existing file.

`tuff pack extract --agent claude` produces `.claude` and `.mcp.json` runtime files without creating Tuff project state. `tuff add pack` instead installs and tracks each member in a project's `tuff.lock` so drift and lifecycle commands continue to work.

## MCP in this example

Model Context Protocol gives Claude a structured way to call a local tool. Tuff renders each tool's manifest into `.mcp.json`; Claude starts `python3 .claude/tools/<id>/server.py` and exchanges JSON-RPC messages over stdin/stdout.

Both example servers support the legacy initialize handshake and the sessionless `2026-07-28` discovery era. They never log to stdout in server mode because stdout is the protocol channel. The same logic is also exposed as a CLI command so hooks, humans, and CI do not need an MCP client.

MCP does not sandbox a tool. The code therefore rejects absolute and traversal paths, avoids executing scanned source, uses allowlisted file types, and emits deterministic reports. A real deployment should still apply operating-system, container, credential, and network controls appropriate to the tool's authority.

## Claude Stop hooks

Tuff maps the pack's canonical `stop` event to Claude's native `Stop` hook and registers a generated wrapper in `.claude/settings.json`. Claude sends JSON on stdin. Exit 0 permits stopping; exit 2 makes stderr available as feedback and asks Claude to continue.

Claude sets `stop_hook_active` when a Stop hook has already caused continuation. Each gate exits 0 in that state to prevent a loop. The gates rerun the installed CLI tool instead of checking whether a report file merely exists, so an old passing report cannot hide current findings.

Hooks execute with the destination user's permissions. Installing a pack never executes them, but using the configured agent does. Consumers should review pack source and pin the reviewed digest before production use.

## What is and is not versioned

The pack versions behavior-shaping capability files. It does not contain the agent application's business code, Python interpreter, Claude executable, cloud runtime configuration, or credentials. Those belong to the application image and deployment platform.

A useful release record therefore stores the application image digest and capability pack digest together. If two agents reuse one reviewed pack, their application images differ while the capability digest remains the same. If behavior guidance changes, the capability release changes even if application code does not.
