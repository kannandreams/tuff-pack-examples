# Policy guardrails with Claude Code

This project shows a Tuff policy changing what a coding agent can do. Claude Code is asked the same question twice: before the policy, it reads `.env` and answers; after `tuff add`, it is denied.

| Capability | Purpose |
| --- | --- |
| `no-env-secrets` policy | Denies reading `.env` files. For Claude Code, Tuff compiles it into a `permissions.deny` rule in `.claude/settings.json`. |

The `.env` used here comes from `fixtures/demo.env`, and its values are fake.

## Watch it

[`demo.mp4`](demo.mp4) is a 46-second recording of the demo below. It is also embedded on [Policies](https://tuffcli.dev/primitives/policies/) in the Tuff documentation.

## Run the demo

Run from this directory:

```sh
./scripts/demo.sh
```

It asks before every step; press Enter to continue or type `n` to stop. Pass `--yes` to run every step without asking.

The demo works in a temporary copy of this project, so it can be repeated and leaves this directory unchanged. The five steps are:

1. Show the fake secret in `.env`.
2. Ask Claude Code for `DEMO_API_KEY`. It reads the file and answers.
3. Add the `no-env-secrets` policy with `tuff add`.
4. Show the rule Tuff wrote to `.claude/settings.json`, then run `tuff check`.
5. Ask Claude Code the same question. It is denied.

Requires Tuff 0.10.0 or newer and Claude Code, signed in. The demo runs Claude Code with `--setting-sources project,local`, so your own `~/.claude` settings do not change the result.

| Option | Effect |
| --- | --- |
| `--yes` | Approve every step; unattended run. |
| `DEMO_MODEL` | Claude model to use. Defaults to `haiku`. |
| `TUFF_COMMAND` | Path to the `tuff` binary. Defaults to `tuff` on `PATH`. |
| `CLAUDE_COMMAND` | Path to the `claude` binary. Defaults to `claude` on `PATH`. |

## Do it by hand

```sh
tuff init
tuff agent add claude
tuff add ./agent-capabilities/no-env-secrets --agent claude
cat .claude/settings.json
```

The policy source stays in `agent-capabilities/`. Tuff writes the Claude Code rule and records it in `tuff.lock`, so `tuff check` reports the rule if someone deletes it by hand, and `tuff delete no-env-secrets` removes exactly that rule.

## What the policy does not cover

Claude Code enforces this rule for its own file tools and for shell commands it recognises, such as `cat`. A script or program that opens `.env` itself is not stopped, and Claude Code's documentation says these rules are not a security boundary. Tuff reports the rule as `partial` for that reason; run `tuff policy matrix` to see the coverage for every agent. When a file must never be reached, also use Claude Code's sandbox.
