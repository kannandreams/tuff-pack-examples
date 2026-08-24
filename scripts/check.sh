#!/bin/sh
set -eu

REPO_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
TUFF_COMMAND=${TUFF_BIN:-tuff}

cd "$REPO_ROOT"
sh -n scripts/build.sh scripts/check.sh scripts/prepare-demo.sh scripts/prepare-image-context.sh
"$TUFF_COMMAND" pack check packs/csv-data-quality
"$TUFF_COMMAND" pack check packs/security-review
python3 -m unittest discover -s tests -v

TEMP_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/tuff-pack-examples-check.XXXXXX")
trap 'rm -rf "$TEMP_ROOT"' EXIT HUP INT TERM

"$TUFF_COMMAND" pack build packs/csv-data-quality --output "$TEMP_ROOT/csv.tuffpack"
"$TUFF_COMMAND" pack verify "$TEMP_ROOT/csv.tuffpack"
"$TUFF_COMMAND" pack build packs/csv-data-quality --output "$TEMP_ROOT/csv-repeat.tuffpack"
cmp "$TEMP_ROOT/csv.tuffpack" "$TEMP_ROOT/csv-repeat.tuffpack"
"$TUFF_COMMAND" pack extract "$TEMP_ROOT/csv.tuffpack" --agent claude --output "$TEMP_ROOT/csv-runtime"

"$TUFF_COMMAND" pack build packs/security-review --output "$TEMP_ROOT/security.tuffpack"
"$TUFF_COMMAND" pack verify "$TEMP_ROOT/security.tuffpack"
"$TUFF_COMMAND" pack build packs/security-review --output "$TEMP_ROOT/security-repeat.tuffpack"
cmp "$TEMP_ROOT/security.tuffpack" "$TEMP_ROOT/security-repeat.tuffpack"
"$TUFF_COMMAND" pack extract "$TEMP_ROOT/security.tuffpack" --agent claude --output "$TEMP_ROOT/security-runtime"

test -f "$TEMP_ROOT/csv-runtime/.claude/tools/csv-quality-check/server.py"
test -f "$TEMP_ROOT/csv-runtime/.claude/hooks/require-data-quality/gate.py"
test -f "$TEMP_ROOT/csv-runtime/.mcp.json"
test -f "$TEMP_ROOT/security-runtime/.claude/tools/security-baseline-scan/server.py"
test -f "$TEMP_ROOT/security-runtime/.claude/hooks/require-security-review/gate.py"
test -f "$TEMP_ROOT/security-runtime/.mcp.json"

cp -R demos/csv-data-quality "$TEMP_ROOT/csv-gate-project"
cp -R "$TEMP_ROOT/csv-runtime/.claude" "$TEMP_ROOT/csv-gate-project/.claude"
cp "$TEMP_ROOT/csv-runtime/.mcp.json" "$TEMP_ROOT/csv-gate-project/.mcp.json"
if printf '%s\n' '{"stop_hook_active":false}' | (cd "$TEMP_ROOT/csv-gate-project" && python3 .claude/hooks/require-data-quality/gate.py); then
  echo "CSV gate unexpectedly accepted the broken fixture" >&2
  exit 1
else
  test "$?" -eq 2
fi
cp "$TEMP_ROOT/csv-gate-project/expected/orders.csv" "$TEMP_ROOT/csv-gate-project/data/orders.csv"
printf '%s\n' '{"stop_hook_active":false}' | (cd "$TEMP_ROOT/csv-gate-project" && python3 .claude/hooks/require-data-quality/gate.py)

cp -R demos/security-review "$TEMP_ROOT/security-gate-project"
cp -R "$TEMP_ROOT/security-runtime/.claude" "$TEMP_ROOT/security-gate-project/.claude"
cp "$TEMP_ROOT/security-runtime/.mcp.json" "$TEMP_ROOT/security-gate-project/.mcp.json"
if printf '%s\n' '{"stop_hook_active":false}' | (cd "$TEMP_ROOT/security-gate-project" && python3 .claude/hooks/require-security-review/gate.py); then
  echo "Security gate unexpectedly accepted the unsafe fixture" >&2
  exit 1
else
  test "$?" -eq 2
fi
cp "$TEMP_ROOT/security-gate-project/expected/service.py" "$TEMP_ROOT/security-gate-project/app/service.py"
printf '%s\n' '{"stop_hook_active":false}' | (cd "$TEMP_ROOT/security-gate-project" && python3 .claude/hooks/require-security-review/gate.py)

echo "All example checks passed."
