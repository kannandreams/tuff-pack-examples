#!/usr/bin/env bash
set -euo pipefail
cd "."
python3 .agents/hooks/require-log-summary/run.py
