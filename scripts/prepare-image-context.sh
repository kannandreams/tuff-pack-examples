#!/bin/sh
set -eu

if [ "$#" -ne 2 ]; then
  echo "usage: $0 OCI_DIGEST_REFERENCE OUTPUT_DIRECTORY" >&2
  exit 2
fi

REFERENCE=$1
OUTPUT=$2
TUFF_COMMAND=${TUFF_BIN:-tuff}
REPO_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)

case "$REFERENCE" in
  *@sha256:*) ;;
  *) echo "use an immutable OCI digest reference containing @sha256:" >&2; exit 2 ;;
esac

if [ -e "$OUTPUT" ]; then
  echo "refusing to overwrite existing output: $OUTPUT" >&2
  exit 2
fi

mkdir -p "$OUTPUT"
"$TUFF_COMMAND" pack pull "$REFERENCE" --output "$OUTPUT/capability.tuffpack"
"$TUFF_COMMAND" pack verify "$OUTPUT/capability.tuffpack"
"$TUFF_COMMAND" pack extract "$OUTPUT/capability.tuffpack" --agent claude --output "$OUTPUT/capability-runtime"
cp "$REPO_ROOT/container/Dockerfile" "$OUTPUT/Dockerfile"

echo "Prepared container build context: $OUTPUT"
