#!/usr/bin/env bash
# Cuts media/interview.mp4 and its captions (SRT) and transcript from the DVIDS source
# ("Virtual Interview Example", https://www.dvidshub.net/video/908962, public domain).
# DVIDS needs a free account to download. Usage:
#   tools/premiere-pro/extract_interview.sh DOD_110058789-1280x720-3000k.mp4 908962.EN_US.webvtt
set -euo pipefail
SRC="$1"; VTT="$2"
OUT="$(dirname "$0")/../../fixtures/premiere-pro/media"
START=44.0   # in the silence before "Hi, Sean"
END=137.0    # in the silence after "...smaller parts from multiple vendors."
ffmpeg -hide_banner -loglevel error -y -ss "$START" -to "$END" -i "$SRC" \
  -c:v libx264 -preset slow -crf 26 -r 25 -g 50 -pix_fmt yuv420p -movflags +faststart \
  -c:a aac -b:a 128k -ar 48000 -map_metadata -1 "$OUT/interview.mp4"
python3 - "$VTT" "$START" "$END" "$OUT" <<'PY'
import re, sys
vtt, start, end, out = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), sys.argv[4]
def secs(s):
    p = s.split(":"); return sum(float(x) * 60 ** i for i, x in enumerate(reversed(p)))
def ts(t, sep="."):
    h, r = divmod(t, 3600); m, s = divmod(r, 60)
    return "%02d:%02d:%06.3f" % (h, m, s) if sep == "." else ("%02d:%02d:%06.3f" % (h, m, s)).replace(".", ",")
cues = re.findall(r"(\S+) --> (\S+)\n(.+?)(?:\n\n|\Z)", open(vtt).read().replace("\r", ""), re.S)
kept = [(max(secs(a), start) - start, min(secs(b), end) - start, t.strip())
        for a, b, t in cues if secs(b) > start and secs(a) < end]
# SRT, because Premiere imports SRT captions but not WebVTT
with open(out + "/interview.srt", "w") as f:
    f.write("".join("%d\n%s --> %s\n%s\n\n" % (i, ts(a, ","), ts(b, ","), t) for i, (a, b, t) in enumerate(kept, 1)))
with open(out + "/interview.txt", "w") as f:
    f.write(re.sub(r"\s+", " ", " ".join(t for _, _, t in kept)).strip() + "\n")
print(len(kept), "cues")
PY
