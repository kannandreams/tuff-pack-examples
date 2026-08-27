#!/usr/bin/env bash
set -euo pipefail
cd -- '.'
exec bash -euo pipefail -c 'python3 .agents/hooks/require-data-quality/gate.py'
