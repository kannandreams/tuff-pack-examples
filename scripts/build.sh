#!/bin/sh
set -eu

if [ "$#" -ne 1 ]; then
  echo "usage: $0 OUTPUT_DIRECTORY" >&2
  exit 2
fi

REPO_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
TUFF_COMMAND=${TUFF_BIN:-tuff}
OUTPUT=$1

case "$OUTPUT" in
  /*) ;;
  *) OUTPUT="$PWD/$OUTPUT" ;;
esac

if [ -d "$OUTPUT" ] && [ -n "$(find "$OUTPUT" -mindepth 1 -maxdepth 1 -print -quit)" ]; then
  echo "output directory must be missing or empty: $OUTPUT" >&2
  exit 2
fi
mkdir -p "$OUTPUT"

cd "$REPO_ROOT/projects/csv-data-quality"
"$TUFF_COMMAND" pack build --name csv-data-quality-capabilities --version 1.0.0 --output "$OUTPUT/csv-data-quality-1.0.0.tuffpack"
"$TUFF_COMMAND" pack verify "$OUTPUT/csv-data-quality-1.0.0.tuffpack"
cd "$REPO_ROOT/projects/security-review"
"$TUFF_COMMAND" pack build --name security-review-capabilities --version 1.0.0 --output "$OUTPUT/security-review-1.0.0.tuffpack"
"$TUFF_COMMAND" pack verify "$OUTPUT/security-review-1.0.0.tuffpack"

echo "Built verified packs in $OUTPUT"
