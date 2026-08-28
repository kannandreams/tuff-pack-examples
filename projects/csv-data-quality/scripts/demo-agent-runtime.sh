#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

auto_approve="${DEMO_AUTO_APPROVE:-0}"
case "${1:-}" in
  --yes|-y)
    auto_approve=1
    ;;
  --help|-h)
    printf 'Usage: %s [--yes]\n\n' "${0##*/}"
    printf '  --yes, -y  skip the confirmation prompt\n'
    exit 0
    ;;
  "")
    ;;
  *)
    printf 'Unknown option: %s\n' "$1" >&2
    printf 'Usage: %s [--yes]\n' "${0##*/}" >&2
    exit 2
    ;;
esac

readonly RESET=$'\033[0m'
readonly DIM=$'\033[2m'
readonly CYAN=$'\033[36m'
readonly GREEN=$'\033[32m'
readonly RUST=$'\033[38;5;202m'
readonly YELLOW=$'\033[33m'
readonly RED=$'\033[31m'

pause_between_steps() {
  sleep "${DEMO_STEP_DELAY:-0.8}"
}

step() {
  printf '\n%s▶ %s%s\n' "$CYAN" "$1" "$RESET"
  pause_between_steps
}

ok() {
  printf '%s✓ %s%s\n' "$GREEN" "$1" "$RESET"
}

note() {
  printf '%s  %s%s\n' "$DIM" "$1" "$RESET"
}

fail() {
  printf '%s✗ %s%s\n' "$RED" "$1" "$RESET" >&2
  exit 1
}

confirm() {
  if [ "$auto_approve" = "1" ]; then
    printf '%s✓ Auto-approved: %s%s\n' "$GREEN" "$1" "$RESET"
    return 0
  fi

  if [ ! -t 0 ]; then
    fail "confirmation required; rerun with --yes for non-interactive use"
  fi

  printf '%s%s [y/N] %s' "$YELLOW" "$1" "$RESET"
  IFS= read -r confirmation
  case "$confirmation" in
    y|Y|yes|YES|Yes)
      ok "Proceeding"
      ;;
    *)
      note "Demo cancelled; no pack was rebuilt or published"
      exit 0
      ;;
  esac
}

run_without_notes() {
  local command_stderr
  if [ "${1:-}" = "tuff" ]; then
    printf '%s$ %s%s\n' "$RUST" "$*" "$RESET"
  fi
  command_stderr="$(mktemp)"
  if ! "$@" 2>"$command_stderr"; then
    cat "$command_stderr" >&2
    rm -f "$command_stderr"
    return 1
  fi
  sed '/^note:/d' "$command_stderr" >&2
  rm -f "$command_stderr"
}

show_capabilities() {
  run_without_notes tuff list
}

for required_command in docker gh jq tuff; do
  command -v "$required_command" >/dev/null 2>&1 || fail "required command not found: $required_command"
done

gh auth status >/dev/null 2>&1 || fail "run 'gh auth login' before starting the demo"
docker info >/dev/null 2>&1 || fail "Docker Desktop is not running"

pack_name="csv-data-quality-capabilities"
pack_version="${PACK_VERSION:-1.0.0}"
pack_path="tuff-dist/${pack_name}-${pack_version}.tuffpack"
runtime_image="${RUNTIME_IMAGE:-csv-data-quality-agent-runtime:demo}"
ghcr_user="$(gh api user --jq .login)"
ghcr_user_lower="$(printf '%s' "$ghcr_user" | tr '[:upper:]' '[:lower:]')"
oci_ref="${CAPABILITY_REF:-ghcr.io/${ghcr_user_lower}/${pack_name}:${pack_version}}"
output_dir="${DEMO_OUTPUT_DIR:-$PROJECT_DIR/demo-output}"
runtime_docker_config="$(mktemp -d)"
trap 'rm -rf "$runtime_docker_config"' EXIT

printf '\n%s%sCSV data-quality agent runtime demo%s\n' "$GREEN" '======== ' "$RESET"
printf '%sMission: Revenue Load Guardian%s\n' "$YELLOW" "$RESET"
note "protect the downstream revenue import by repairing only authoritative CSV issues"
note "project: $PROJECT_DIR"
note "pack:    $oci_ref"
note "delay:   ${DEMO_STEP_DELAY:-0.8}s per step"

step "Navigate to the demo project and list its capabilities"
show_capabilities
ok "Tuff project is ready"
confirm "Proceed with pack build, registry publish, and sandbox run?"

step "Build and verify the capability pack"
run_without_notes tuff check
if [ -f "$pack_path" ]; then
  note "replacing existing generated artifact: $pack_path"
  rm -f "$pack_path"
fi
run_without_notes tuff pack build --name "$pack_name" --version "$pack_version"
run_without_notes tuff pack verify "$pack_path"
run_without_notes tuff pack inspect "$pack_path"
ok "Pack contains the verified open-agents target"

step "Create temporary GitHub Container Registry credentials"
gh_token="$(gh auth token)"
gh_auth="$(printf '%s' "$ghcr_user:$gh_token" | base64 | tr -d '\n')"
jq -n --arg auth "$gh_auth" \
  '{auths:{"ghcr.io":{auth:$auth}}}' \
  > "$runtime_docker_config/config.json"
chmod 600 "$runtime_docker_config/config.json"
unset gh_token gh_auth
ok "Using the existing gh login; Docker Desktop credential helpers are bypassed"

step "Publish the pack as an OCI artifact to GitHub Container Registry"
DOCKER_CONFIG="$runtime_docker_config" \
  run_without_notes tuff pack push "$pack_path" "$oci_ref"
ok "Published $oci_ref"

step "Build the isolated agent runtime image"
docker build -f Dockerfile.agent-runtime -t "$runtime_image" .
docker image ls "$runtime_image"
ok "Runtime image is available locally"

step "Start the sandbox and let the agent fetch its capabilities"
mkdir -p "$output_dir"
rm -f "$output_dir/orders.csv" "$output_dir/data-quality.json"

docker run --rm -i \
  -e CAPABILITY_REF="$oci_ref" \
  -e DEMO_STEP_DELAY="${DEMO_STEP_DELAY:-0.8}" \
  -e DOCKER_CONFIG=/root/.docker \
  -v "$PROJECT_DIR:/input:ro" \
  -v "$output_dir:/output" \
  -v "$runtime_docker_config:/root/.docker:ro" \
  "$runtime_image" bash -s <<'CONTAINER_SCRIPT'
set -euo pipefail

readonly RESET=$'\033[0m'
readonly CYAN=$'\033[36m'
readonly GREEN=$'\033[32m'
readonly RUST=$'\033[38;5;202m'
step() {
  printf '\n%s▶ %s%s\n' "$CYAN" "$1" "$RESET"
  sleep "${DEMO_STEP_DELAY:-0.8}"
}
ok() {
  printf '%s✓ %s%s\n' "$GREEN" "$1" "$RESET"
}
run_without_notes() {
  local command_stderr
  if [ "${1:-}" = "tuff" ]; then
    printf '%s$ %s%s\n' "$RUST" "$*" "$RESET"
  fi
  command_stderr="$(mktemp)"
  if ! "$@" 2>"$command_stderr"; then
    cat "$command_stderr" >&2
    rm -f "$command_stderr"
    return 1
  fi
  sed '/^note:/d' "$command_stderr" >&2
  rm -f "$command_stderr"
}
show_capabilities() {
  run_without_notes tuff list
}

mkdir -p /work
cp -R /input/TASK.md /input/data /input/expected /input/.tuff-example /work/
cd /work

step "Initialize a clean agent project"
run_without_notes tuff init

step "Agent mission: protect the downstream revenue load"
printf '  inspect the extract, repair authoritative issues, and block bad data from release\n'

step "Pull and verify the published capability pack"
run_without_notes tuff pack pull "$CAPABILITY_REF" -o /tmp/csv-data-quality.tuffpack
run_without_notes tuff pack verify /tmp/csv-data-quality.tuffpack
run_without_notes tuff add pack /tmp/csv-data-quality.tuffpack -a open-agents
show_capabilities
ok "The runtime fetched and installed the capabilities"

step "Run the checker before the agent edits the CSV"
set +e
python3 .agents/tools/csv-quality-check/server.py check \
  --policy .tuff-example/data-quality-policy.json \
  --output .tuff-reports/data-quality.json
initial_status=$?
set -e
test "$initial_status" -eq 1
ok "The expected initial quality findings were detected"

step "Apply the task corrections in the sandbox"
python3 - <<'PY'
import csv
from pathlib import Path

path = Path("data/orders.csv")
rows = list(csv.DictReader(path.open(newline="", encoding="utf-8")))
rows[1]["customer_id"] = "c-2"
rows[2]["order_id"] = "1003"
rows[2]["amount"] = "5.00"
rows[3]["amount"] = "25.00"
with path.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=["order_id", "customer_id", "amount", "currency"])
    writer.writeheader()
    writer.writerows(rows)
PY
printf '%sChanges applied:%s\n' "$GREEN" "$RESET"
printf '  - assigned order 1002 to customer c-2\n'
printf '  - corrected the duplicate order ID to 1003\n'
printf '  - corrected order 1003 amount to 5.00\n'
printf '  - corrected order 1004 amount to 25.00\n'
ok "The agent repaired the governed CSV"

step "Run the final tool check and before-finish gate"
python3 .agents/tools/csv-quality-check/server.py check \
  --policy .tuff-example/data-quality-policy.json \
  --output .tuff-reports/data-quality.json
sh .agents/hooks/require-data-quality/run.sh
ok "Quality check passed and the finish gate permitted completion"

mkdir -p /output
cp data/orders.csv /output/orders.csv
cp .tuff-reports/data-quality.json /output/data-quality.json
printf '\nFinal sandbox artifacts:\n'
ls -lh /output
CONTAINER_SCRIPT

step "Show the exported agent result"
cat "$output_dir/data-quality.json"
printf '\n%sArtifacts saved under %s%s\n' "$GREEN" "$output_dir" "$RESET"
