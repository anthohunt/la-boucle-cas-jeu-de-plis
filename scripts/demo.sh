#!/bin/bash
# One complete turn of the example loop: games -> measure -> keep/discard -> journal -> HTML dashboard.
# usage: scripts/demo.sh [workdir] [passes]
set -euo pipefail
cd "$(dirname "$0")/.."
W="${1:-run}"; N="${2:-3}"
python3 -m trickloop measure --bot rules --games 200      # the meter checks itself (about 25 %)
python3 -m trickloop loop --workdir "$W" --passes "$N" --preset fast
echo "journal:   $W/journal.jsonl"
echo "dashboard: $W/dashboard.html"
