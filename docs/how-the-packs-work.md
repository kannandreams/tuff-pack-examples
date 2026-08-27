# How these packs work

## Why one repository can contain multiple agent projects

A repository is a source-control boundary; an agent project and a pack are behavior and release boundaries. They do not have to be one-to-one. This repository keeps two independent initialized projects together while each project has its own `tuff.lock`, default agent, capability sources, and release name.

That means a CSV capability change can release `csv-data-quality-capabilities` 1.0.1 without changing or republishing `security-review-capabilities` 1.0.0. Consumers choose a pack reference, not the whole Git repository.

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
hook: reruns the measurement before the agent finishes
   |
   +-- pass --> agent may finish
   |
   +-- fail --> exit 2 feedback asks the agent to continue

workflow: declares that skill + tool + hook must be packaged together
```

The security example uses the same shape but preserves an important distinction: the tool finds pattern signals, while the skill performs contextual security reasoning. A baseline scanner cannot establish exploitability and a clean scan cannot prove security.

## What Tuff does at each stage

`tuff check` validates the project’s tracked capabilities, rendered files, hook registrations, and accepted state. It does not run capability code.

`tuff pack build --name ...` selects accepted project capabilities from `tuff.lock`, reconstructs their portable sources, and creates a deterministic `.tuffpack` with the project’s configured target. The same accepted inputs produce the same pack digest; `scripts/check.sh` builds every project twice and compares the bytes.

`tuff pack verify` validates the artifact structure, canonical metadata, file digests, and overall artifact digest.

`tuff pack push` puts those exact bytes into a generic OCI artifact. Authentication comes from `docker login` or `podman login`. Tuff returns the artifact digest and an immutable OCI manifest digest reference.

`tuff pack pull` downloads by tag or digest, validates the OCI descriptors and Tuff artifact, and writes atomically without overwriting an existing file.

`tuff pack extract --agent <id>` produces harness-native runtime files without creating Tuff project state. `tuff add pack` instead installs and tracks each member in a consumer project’s `tuff.lock` so drift and lifecycle commands continue to work.

## MCP in these examples

Model Context Protocol gives an agent a structured way to call a local tool. Tuff renders Claude configuration into `.mcp.json` and Open Agents configuration into `.agents/mcp.json`. Each harness starts the corresponding Python server under its generated tool directory and exchanges JSON-RPC messages over stdin/stdout.

Both example servers support the legacy initialize handshake and the sessionless `2026-07-28` discovery era. They never log to stdout in server mode because stdout is the protocol channel. The same logic is also exposed as a CLI command so hooks, humans, and CI do not need an MCP client.

MCP does not sandbox a tool. The code therefore rejects absolute and traversal paths, avoids executing scanned source, uses allowlisted file types, and emits deterministic reports. A real deployment should still apply operating-system, container, credential, and network controls appropriate to the tool's authority.

## Harness-specific finish hooks

The security project uses the canonical `stop` event, which Tuff maps to Claude’s native `Stop` hook in `.claude/settings.json`. Claude sends JSON on stdin; `stop_hook_active` prevents recursive continuation loops.

The CSV project uses Open Agents’ supported `before_finish` event in `.agents/hook.json`. Both gates rerun the installed CLI tool instead of trusting an old report. Exit 0 permits finishing, while exit 2 returns actionable feedback.

Hooks execute with the destination user's permissions. Installing a pack never executes them, but using the configured agent does. Consumers should review pack source and pin the reviewed digest before production use.

## What is and is not versioned

The pack versions behavior-shaping capability files. It does not contain the agent application's business code, Python interpreter, Claude executable, cloud runtime configuration, or credentials. Those belong to the application image and deployment platform.

A useful release record therefore stores the application image digest and capability pack digest together. If two agents reuse one reviewed pack, their application images differ while the capability digest remains the same. If behavior guidance changes, the capability release changes even if application code does not.
