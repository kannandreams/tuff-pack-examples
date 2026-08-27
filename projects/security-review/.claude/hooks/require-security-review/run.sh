#!/usr/bin/env bash
set -euo pipefail
cd -- '.'
exec bash -euo pipefail -c 'python3 .claude/hooks/require-security-review/gate.py'
