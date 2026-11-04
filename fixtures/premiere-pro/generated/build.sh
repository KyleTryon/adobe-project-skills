#!/usr/bin/env bash
# Builds the generated projects waiting to be checked, from the steps, using only
# skills/premiere-pro-projects/scripts/prproj.py (no Premiere). Open each in Premiere and
# check it against CHECKLIST.md. Once one checks out, it moves to ../steps/ as
# NN-gen-*.prproj (scrubbed) and its commands become a case in tests/premiere-pro/replay_steps.py.
#
#   ./build.sh            # paths as committed (/Users/editor/adobe-project-skills/...); media links via ../media
#   ./build.sh --local    # also point those paths at this repo and your home folder, so Premiere
#                         # finds the media without asking
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../../.." && pwd)"
STEPS="$HERE/../steps"
P() { python3 -I "$ROOT/skills/premiere-pro-projects/scripts/prproj.py" "$@" 2>&1 | sed 's/^/    /'; }
S=clip-a

# Nothing waiting: every generated project so far has been checked and moved to ../steps/.

if [ "${1:-}" = "--local" ]; then
  python3 -I - "$HERE" "${LOCAL_HOME:-$HOME}" "$ROOT" <<'PY'
import glob, gzip, os, sys
here, home, root = sys.argv[1], sys.argv[2].rstrip('/') + '/', sys.argv[3].rstrip('/')
for f in glob.glob(os.path.join(here, '*.prproj')):
    x = gzip.decompress(open(f, 'rb').read()).decode('utf-8')
    x = x.replace('/Users/editor/adobe-project-skills', root).replace('/Users/editor/', home)
    open(f, 'wb').write(gzip.compress(x.encode('utf-8')))
print(f"    media paths point at {root}")
PY
fi
shopt -s nullglob
for f in "$HERE"/*.prproj; do
  python3 -I "$ROOT/skills/premiere-pro-projects/scripts/prproj.py" validate "$f" >/dev/null 2>&1 \
    && echo "valid: $(basename "$f")" || { echo "INVALID: $f"; exit 1; }
done
