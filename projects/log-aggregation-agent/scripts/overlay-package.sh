#!/usr/bin/env bash
# Composite a screenshot of the GHCR package page into the recorded demo as a
# picture-in-picture, so the video shows the real GitHub Packages window at the
# moment the pack is published. VHS records only the terminal, so the browser
# has to be captured separately.
#
# Usage: scripts/overlay-package.sh SHOT.png [START_SECONDS] [DURATION_SECONDS] [IN.mp4] [OUT.mp4]
set -euo pipefail

shot=${1:?usage: overlay-package.sh SHOT.png [start] [duration] [in.mp4] [out.mp4]}
start=${2:-0}
duration=${3:-8}
input=${4:-demo.mp4}
out=${5:-demo-with-package.mp4}
end=$(python3 -c "print(float('$start') + float('$duration'))")

cd "$(dirname "$0")/.."
ffmpeg -y -i "$input" -i "$shot" -filter_complex \
  "[1:v]scale=w=620:h=-2,format=rgba,colorchannelmixer=aa=0.97[pip];\
   [0:v][pip]overlay=x=W-w-40:y=H-h-40:enable='between(t,${start},${end})'" \
  -c:v libx264 -pix_fmt yuv420p -crf 20 -an "$out"

echo "wrote $out (package window visible ${start}s → ${end}s)"
