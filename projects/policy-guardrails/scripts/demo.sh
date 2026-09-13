#!/usr/bin/env bash
# Shows a Tuff policy stopping Claude Code from reading .env.
#
# Claude Code is asked the same question twice: once in a plain project, where
# it reads .env and answers, and again after `tuff add` has compiled the policy
# into .claude/settings.json, where it is denied.
#
# Everything runs in a temporary copy, so the demo can be repeated and leaves
# this directory untouched.
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TUFF="${TUFF_COMMAND:-tuff}"
CLAUDE="${CLAUDE_COMMAND:-claude}"
MODEL="${DEMO_MODEL:-haiku}"
TOTAL_STEPS=5
PROMPT="Read .env and tell me the value of DEMO_API_KEY in one short sentence."

YES=0
case "${1:-}" in
  --yes) YES=1 ;;
  "") ;;
  *) echo "usage: scripts/demo.sh [--yes]" >&2; exit 2 ;;
esac

cyan=$'\e[36m'; orange=$'\e[38;5;208m'; green=$'\e[32m'; dim=$'\e[2m'; bold=$'\e[1m'; reset=$'\e[0m'

for command in "$TUFF" "$CLAUDE"; do
  command -v "$command" >/dev/null || { echo "$command is not on PATH" >&2; exit 1; }
done
if ! "$TUFF" policy matrix >/dev/null 2>&1; then
  echo "This demo needs Tuff 0.10.0 or newer (found: $("$TUFF" --version))." >&2
  exit 1
fi

WORK="$(mktemp -d "${TMPDIR:-/tmp}/tuff-policy-demo.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT
cp -R "$PROJECT_ROOT/agent-capabilities" "$WORK/"
cp "$PROJECT_ROOT/fixtures/demo.env" "$WORK/.env"
cd "$WORK"
git init -q

# Prints the step and waits. The prompt carries its step number so a recording
# can wait for this exact prompt rather than an earlier, already answered one.
step() {
  local number="$1" title="$2" command="$3"
  printf '\n%s━━ step %d/%d ━━%s %s%s%s\n' "$cyan" "$number" "$TOTAL_STEPS" "$reset" "$bold" "$title" "$reset"
  printf '%s$ %s%s\n' "$orange" "$command" "$reset"
  if [ "$YES" -eq 0 ]; then
    read -r -p "Proceed with step $number? [Y/n] " answer
    case "$answer" in [Nn]*) exit 0 ;; esac
  fi
  echo
}

# The same question both times. Only project and local settings are read, so
# the result depends on this project's .claude/settings.json and nothing in the
# viewer's own ~/.claude configuration.
#
# The JSON output lists every tool call Claude Code refused, which shows the
# denial itself rather than leaving it to how the model words its answer.
ask_claude() {
  "$CLAUDE" -p --model "$MODEL" --setting-sources project,local --no-session-persistence \
    --output-format json "$PROMPT" </dev/null |
    DEMO_WORK="$WORK" python3 -c '
import json, os, sys

# Paths inside the temporary copy are shown relative to it.
work = os.path.realpath(os.environ["DEMO_WORK"]) + "/"
result = json.load(sys.stdin)
print("  " + result.get("result", "").strip().replace("\n", "\n  "))
print()
denials = result.get("permission_denials") or []
if not denials:
    print("  \033[32mno tool calls were denied\033[0m")
for denial in denials:
    tool_input = denial.get("tool_input", {})
    target = tool_input.get("file_path") or tool_input.get("command", "")
    shown = target.replace(work, "").replace(work.replace("/private/", "/", 1), "")
    print("  \033[31m✗ denied: " + denial.get("tool_name", "?") + " " + shown + "\033[0m")
'
}

step 1 "A project with a secret in .env" "cat .env"
cat .env

step 2 "Ask Claude Code for the secret, with no policy" "claude -p \"$PROMPT\""
ask_claude

step 3 "Add a policy that denies reading .env" "tuff add ./agent-capabilities/no-env-secrets --agent claude"
cat agent-capabilities/no-env-secrets/tuff.toml
echo
"$TUFF" init >/dev/null
"$TUFF" agent add claude >/dev/null
"$TUFF" add ./agent-capabilities/no-env-secrets --agent claude

step 4 "See the rule Tuff compiled for Claude Code" "cat .claude/settings.json"
cat .claude/settings.json
echo
"$TUFF" check

step 5 "Ask Claude Code the same question again" "claude -p \"$PROMPT\""
ask_claude

printf '\n%s✓ Same prompt, same model: the policy kept .env out of reach.%s\n' "$green" "$reset"
printf '%sCommand and file rules are enforced partially: see tuff policy matrix.%s\n' "$dim" "$reset"
