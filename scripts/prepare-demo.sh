#!/bin/sh
set -eu

if [ "$#" -ne 1 ]; then
  echo "usage: $0 csv-data-quality|security-review" >&2
  exit 2
fi

DEMO=$1
case "$DEMO" in
  csv-data-quality|security-review) ;;
  *) echo "unknown demo: $DEMO" >&2; exit 2 ;;
esac

REPO_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
TUFF_COMMAND=${TUFF_BIN:-tuff}
DESTINATION="$REPO_ROOT/.work/$DEMO"

if [ -e "$DESTINATION" ]; then
  echo "refusing to overwrite existing demo: $DESTINATION" >&2
  exit 2
fi

mkdir -p "$REPO_ROOT/.work"
cp -R "$REPO_ROOT/demos/$DEMO" "$DESTINATION"

TEMP_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/tuff-pack-demo.XXXXXX")
trap 'rm -rf "$TEMP_ROOT"' EXIT HUP INT TERM

"$TUFF_COMMAND" pack build "$REPO_ROOT/packs/$DEMO" --output "$TEMP_ROOT/$DEMO.tuffpack"
cd "$DESTINATION"
"$TUFF_COMMAND" init
"$TUFF_COMMAND" agent add claude
"$TUFF_COMMAND" agent set-default claude
"$TUFF_COMMAND" add pack "$TEMP_ROOT/$DEMO.tuffpack" --agent claude
"$TUFF_COMMAND" check

echo "Prepared $DESTINATION"
echo "Next: cd $DESTINATION && claude"
