# Run an agent in a sandbox

This example runs the CSV data-quality agent contract in an isolated Docker
container. The container pulls the capability pack from an OCI registry,
installs the `open-agents` target, and works on a disposable copy of the
project. The host checkout is mounted read-only.

This is a deterministic agent-session harness. It demonstrates the portable
Open Agents contract without requiring a model API key or selecting one
vendor's agent product. Codex, GitHub Copilot, and other supported agents can
use the same installed `.agents/` files when they are available in the
runtime.

The agent's purpose is to act as a **Revenue Load Guardian**: protect a
downstream revenue import by inspecting the source extract, applying only the
authoritative corrections in `TASK.md`, and blocking completion until the
quality policy passes. In this fixture it repairs customer ownership, a
duplicate order ID, and two invalid amounts.

## Prerequisites

- Docker
- An OCI reference containing this pack, supplied as `CAPABILITY_REF`
- Registry credentials that can pull the pack

```sh
export CAPABILITY_REF=docker.io/kannandreams/csv-data-quality-capabilities:1.0
```

Use a digest instead of a tag when the runtime must be fully immutable.

## Build the runtime image

Run this from the project root:

```sh
docker build -f Dockerfile.agent-runtime \
  -t csv-data-quality-agent-runtime:local .
```

The image contains Python 3.12 and builds Tuff CLI from the configured GitHub
repository. It does not contain host credentials or project files. Set
`--build-arg TUFF_REF=<commit-or-branch>` when building if you need to pin the
runtime to a particular Tuff revision.

## Prepare registry credentials

Tuff reads Docker-compatible registry credentials. On a GitHub-hosted Linux
runner, `docker/login-action` normally creates a usable `auths` entry. On
macOS, Docker Desktop may configure a keychain helper that is unavailable to
Tuff. For a local run, create a short-lived helper-free config:

```sh
runtime_docker_config="$(mktemp -d)"
read -s docker_pat
printf '\n'
docker_auth="$(printf '%s' "kannandreams:$docker_pat" | base64)"
jq --arg auth "$docker_auth" \
  '.auths["https://index.docker.io/v1/"] = {auth: $auth}
   | del(.credsStore, .credHelpers)' \
  <(printf '%s\n' '{"auths":{}}') \
  > "$runtime_docker_config/config.json"
unset docker_pat docker_auth
```

Keep this directory until the run completes. Remove it in the cleanup step.

## Start the sandbox

The input checkout is read-only; `/work` exists only inside the container,
and `/output` is the only writable host mount.

```sh
mkdir -p agent-runtime-output
docker run --rm -it \
  -e CAPABILITY_REF \
  -e DOCKER_CONFIG=/root/.docker \
  -v "$PWD:/input:ro" \
  -v "$PWD/agent-runtime-output:/output" \
  -v "$runtime_docker_config:/root/.docker:ro" \
  csv-data-quality-agent-runtime:local
```

Run the following inside the container:

```sh
set -euo pipefail
mkdir -p /work
cp -R /input/TASK.md /input/data /input/expected /input/.tuff-example /work/
cd /work

tuff init
tuff pack pull "$CAPABILITY_REF" -o /tmp/csv-data-quality.tuffpack
tuff pack verify /tmp/csv-data-quality.tuffpack
tuff add pack /tmp/csv-data-quality.tuffpack -a open-agents
tuff list

# The initial data is intentionally invalid; status 1 means findings exist.
set +e
python3 .agents/tools/csv-quality-check/server.py check \
  --policy .tuff-example/data-quality-policy.json \
  --output .tuff-reports/data-quality.json
initial_status=$?
set -e
test "$initial_status" -eq 1

# Deterministic stand-in for the agent's edit. The production agent would
# derive the same changes from TASK.md and csv-workbench/SKILL.md.
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

python3 .agents/tools/csv-quality-check/server.py check \
  --policy .tuff-example/data-quality-policy.json \
  --output .tuff-reports/data-quality.json
sh .agents/hooks/require-data-quality/run.sh

mkdir -p /output
cp data/orders.csv /output/orders.csv
cp .tuff-reports/data-quality.json /output/data-quality.json
```

Exit the shell and remove the temporary credential config:

```sh
rm -rf "$runtime_docker_config"
```

The final report has `status: "pass"`, `row_count: 4`, zero findings, and a
corrected total of `87.50 GBP`.

## GitHub-hosted runner

The same container can run in GitHub Actions. This is a documented example,
not a committed workflow file:

```yaml
- uses: actions/checkout@v4

- uses: docker/login-action@v3
  with:
    registry: docker.io
    username: ${{ secrets.DOCKERHUB_USERNAME }}
    password: ${{ secrets.DOCKERHUB_TOKEN }}

- name: Build agent runtime
  run: docker build -f Dockerfile.agent-runtime -t csv-data-quality-agent-runtime:ci .

- name: Run sandboxed agent session
  env:
    CAPABILITY_REF: ${{ vars.CAPABILITY_REF }}
  run: |
    mkdir -p "$RUNNER_TEMP/csv-data-quality-output"
    docker run --rm \
      -e CAPABILITY_REF \
      -e DOCKER_CONFIG=/root/.docker \
      -v "$GITHUB_WORKSPACE:/input:ro" \
      -v "$RUNNER_TEMP/csv-data-quality-output:/output" \
      -v "$HOME/.docker:/root/.docker:ro" \
      csv-data-quality-agent-runtime:ci \
      bash -lc 'set -euo pipefail
        mkdir -p /work
        cp -R /input/TASK.md /input/data /input/expected /input/.tuff-example /work/
        cd /work
        tuff init
        tuff pack pull "$CAPABILITY_REF" -o /tmp/capabilities.tuffpack
        tuff pack verify /tmp/capabilities.tuffpack
        tuff add pack /tmp/capabilities.tuffpack -a open-agents
        tuff check
        python3 -c "import csv; from pathlib import Path; p=Path('data/orders.csv'); rows=list(csv.DictReader(p.open(newline='', encoding='utf-8'))); rows[1]['customer_id']='c-2'; rows[2]['order_id']='1003'; rows[2]['amount']='5.00'; rows[3]['amount']='25.00'; f=p.open('w', newline='', encoding='utf-8'); w=csv.DictWriter(f, fieldnames=['order_id','customer_id','amount','currency']); w.writeheader(); w.writerows(rows); f.close()"
        python3 .agents/tools/csv-quality-check/server.py check \
          --policy .tuff-example/data-quality-policy.json \
          --output .tuff-reports/data-quality.json
        sh .agents/hooks/require-data-quality/run.sh
        cp data/orders.csv /output/orders.csv
        cp .tuff-reports/data-quality.json /output/data-quality.json'
```

In a real model-backed agent job, replace the deterministic edit/check
sequence with the selected agent runner. The pack pull, `open-agents` target,
project-relative paths, tool invocation, and finish hook remain the same.
