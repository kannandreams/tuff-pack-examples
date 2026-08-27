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
ARTIFACT_DIRECTORY="$REPO_ROOT/.work/artifacts"
PACK_VERSION=$(sed -n 's/^version = "\([^"]*\)"$/\1/p' "$REPO_ROOT/packs/$DEMO/tuff-pack.toml" | head -n 1)
ARTIFACT="$ARTIFACT_DIRECTORY/$DEMO-$PACK_VERSION.tuffpack"

if [ -e "$DESTINATION" ]; then
  echo "refusing to overwrite existing demo: $DESTINATION" >&2
  exit 2
fi

if [ -e "$ARTIFACT" ]; then
  echo "refusing to overwrite existing artifact: $ARTIFACT" >&2
  exit 2
fi

mkdir -p "$ARTIFACT_DIRECTORY"
cp -R "$REPO_ROOT/demos/$DEMO" "$DESTINATION"

"$TUFF_COMMAND" pack build "$REPO_ROOT/packs/$DEMO" --output "$ARTIFACT"
"$TUFF_COMMAND" pack verify "$ARTIFACT"
cd "$DESTINATION"
"$TUFF_COMMAND" init
"$TUFF_COMMAND" agent add claude
"$TUFF_COMMAND" agent set-default claude
"$TUFF_COMMAND" add pack "$ARTIFACT" --agent claude
"$TUFF_COMMAND" check

echo "Prepared $DESTINATION"
echo "Kept pack artifact at $ARTIFACT"
echo "Next: cd $DESTINATION && claude"
