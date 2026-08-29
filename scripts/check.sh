#!/bin/sh
set -eu

REPO_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
TUFF_COMMAND=${TUFF_BIN:-tuff}

cd "$REPO_ROOT"
sh -n scripts/build.sh scripts/check.sh scripts/prepare-image-context.sh
python3 -m unittest discover -s tests -v

TEMP_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/tuff-pack-examples-check.XXXXXX")
trap 'rm -rf "$TEMP_ROOT"' EXIT HUP INT TERM

cd "$REPO_ROOT/projects/csv-data-quality"
"$TUFF_COMMAND" check
"$TUFF_COMMAND" pack build --name csv-data-quality-capabilities --version 1.0.0 --output "$TEMP_ROOT/csv.tuffpack"
"$TUFF_COMMAND" pack verify "$TEMP_ROOT/csv.tuffpack"
"$TUFF_COMMAND" pack build --name csv-data-quality-capabilities --version 1.0.0 --output "$TEMP_ROOT/csv-repeat.tuffpack"
cmp "$TEMP_ROOT/csv.tuffpack" "$TEMP_ROOT/csv-repeat.tuffpack"
"$TUFF_COMMAND" pack extract "$TEMP_ROOT/csv.tuffpack" --agent open-agents --output "$TEMP_ROOT/csv-runtime"

cd "$REPO_ROOT/projects/security-review"
"$TUFF_COMMAND" check
"$TUFF_COMMAND" pack build --name security-review-capabilities --version 1.0.0 --output "$TEMP_ROOT/security.tuffpack"
"$TUFF_COMMAND" pack verify "$TEMP_ROOT/security.tuffpack"
"$TUFF_COMMAND" pack build --name security-review-capabilities --version 1.0.0 --output "$TEMP_ROOT/security-repeat.tuffpack"
cmp "$TEMP_ROOT/security.tuffpack" "$TEMP_ROOT/security-repeat.tuffpack"
"$TUFF_COMMAND" pack extract "$TEMP_ROOT/security.tuffpack" --agent claude --output "$TEMP_ROOT/security-runtime"

test -f "$TEMP_ROOT/csv-runtime/.agents/tools/csv-quality-check/server.py"
test -f "$TEMP_ROOT/csv-runtime/.agents/hooks/require-data-quality/gate.py"
test -f "$TEMP_ROOT/csv-runtime/.agents/mcp.json"
test -f "$TEMP_ROOT/security-runtime/.claude/tools/security-baseline-scan/server.py"
test -f "$TEMP_ROOT/security-runtime/.claude/hooks/require-security-review/gate.py"
test -f "$TEMP_ROOT/security-runtime/.mcp.json"

cp -R "$REPO_ROOT/projects/csv-data-quality" "$TEMP_ROOT/csv-gate-project"
cp "$TEMP_ROOT/csv-gate-project/data/orders-extract.csv" "$TEMP_ROOT/csv-gate-project/data/orders.csv"
rm -f "$TEMP_ROOT/csv-gate-project/data/quarantine.csv"
if (cd "$TEMP_ROOT/csv-gate-project" && python3 .agents/hooks/require-data-quality/gate.py); then
  echo "CSV gate unexpectedly accepted the untriaged extract" >&2
  exit 1
else
  test "$?" -eq 2
fi
# Write one correct triage. The project ships no expected result: releasing a
# row the extract cannot justify is exactly what the gate must reject, so the
# answer is constructed here rather than stored next to the data.
cat > "$TEMP_ROOT/csv-gate-project/data/orders.csv" <<'CSV'
order_id,customer_id,amount,currency
1001,c-1,42.50,GBP
1002,c-2,15.00,GBP
1003,c-3,8.25,GBP
1004,c-4,25.00,GBP
CSV
cat > "$TEMP_ROOT/csv-gate-project/data/quarantine.csv" <<'CSV'
source_row,order_id,reason
6,1004,exact duplicate of source row 5
7,1005,customer_id is empty
8,1006,amount is not a number
9,1007,amount is below the policy minimum
10,1008,currency JPY has no conversion rate
11,1009,conflicting duplicate
12,1009,conflicting duplicate
CSV
(cd "$TEMP_ROOT/csv-gate-project" && python3 .agents/hooks/require-data-quality/gate.py)

cp -R "$REPO_ROOT/projects/security-review" "$TEMP_ROOT/security-gate-project"
if printf '%s\n' '{"stop_hook_active":false}' | (cd "$TEMP_ROOT/security-gate-project" && python3 .claude/hooks/require-security-review/gate.py); then
  echo "Security gate unexpectedly accepted the unsafe fixture" >&2
  exit 1
else
  test "$?" -eq 2
fi
cp "$TEMP_ROOT/security-gate-project/expected/service.py" "$TEMP_ROOT/security-gate-project/app/service.py"
printf '%s\n' '{"stop_hook_active":false}' | (cd "$TEMP_ROOT/security-gate-project" && python3 .claude/hooks/require-security-review/gate.py)

echo "All example checks passed."
