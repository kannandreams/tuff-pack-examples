# Security-review agent project

This initialized Tuff project demonstrates a reusable security-review capability layer for Claude Code (`.claude/`).

| Capability | Purpose |
| --- | --- |
| `security-review` skill | Guides contextual review, validation, severity, and human approval. |
| `security-baseline-scan` tool | Reports a deterministic set of security signals through a CLI and MCP server. |
| `require-security-review` hook | Reruns the scanner when Claude tries to stop. |
| `secure-release-review` workflow | Declares that the skill, tool, and hook travel together. |

The baseline scanner is not a security guarantee. Pattern matches require contextual validation, and a clean baseline does not prove that an application is secure.

## Build the pack

Run from this directory:

```sh
tuff list
tuff check
tuff pack build --name security-review-capabilities --version 1.0.0
tuff pack verify tuff-dist/security-review-capabilities-1.0.0.tuffpack
tuff pack inspect tuff-dist/security-review-capabilities-1.0.0.tuffpack
```

The project default is `claude`, so the artifact contains a Claude target without requiring `--agent`.

## See how it was initialized

The project already contains the result of these commands:

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

The portable source stays in `agent-capabilities/`; Tuff renders the selected harness into `.claude/` and records the accepted state in `tuff.lock`. No `tuff-pack.toml` or separate pack directory is involved.

## Try the deterministic scanner

The starting service contains fake credential text and intentionally unsafe Python patterns:

```sh
python3 .claude/tools/security-baseline-scan/server.py check
```

Exit status `1` is expected until `app/service.py` is corrected. The passing fixture is under `expected/service.py`. Never use fixture values as real credentials.
