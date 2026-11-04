#!/usr/bin/env bash
# Generates the synthetic demo media for fixtures/premiere-pro/media/
# (interview.* comes from tools/premiere-pro/extract_interview.sh instead).
# Needs ffmpeg (with libx264 and drawtext). Output is deterministic
# apart from encoder metadata. Usage: tools/premiere-pro/make_media.sh [OUTDIR]
set -euo pipefail
OUT="${1:-$(dirname "$0")/../../fixtures/premiere-pro/media}"
mkdir -p "$OUT"
FONT="${FONT:-$(fc-match -f '%{file}' 'DejaVu Sans:bold')}"
MONO="${MONO:-$(fc-match -f '%{file}' 'DejaVu Sans Mono:bold')}"
FF=(ffmpeg -hide_banner -loglevel error -y)
V264=(-c:v libx264 -preset veryfast -crf 30 -pix_fmt yuv420p -movflags +faststart)
A=(-c:a aac -b:a 128k -ar 48000)

# Burned-in label, timecode and frame number: cuts and trims can be checked by eye.
burn() { # $1 label  $2 rate (e.g. 24000/1001)  $3 fps text
  echo "drawtext=fontfile=$FONT:text='$1':fontsize=h/4:fontcolor=white:borderw=8:bordercolor=black:x=(w-tw)/2:y=h*0.18,\
drawtext=fontfile=$MONO:timecode='00\:00\:00\:00':rate=$2:fontsize=h/9:fontcolor=white:box=1:boxcolor=black@0.7:boxborderw=20:x=(w-tw)/2:y=h*0.58,\
drawtext=fontfile=$MONO:text='frame %{frame_num}   $3 fps':fontsize=h/18:fontcolor=white:box=1:boxcolor=black@0.7:boxborderw=12:x=(w-tw)/2:y=h*0.78"
}

# clip-a: 1080p 23.976, 20 s, test pattern, 1 kHz beep on every whole second (sync check)
"${FF[@]}" -f lavfi -i "testsrc2=size=1920x1080:rate=24000/1001:duration=20" \
  -f lavfi -i "aevalsrc='0.1*sin(2*PI*1000*t)*lt(mod(t\,1)\,0.1)|0.1*sin(2*PI*1000*t)*lt(mod(t\,1)\,0.1)':s=48000:d=20" \
  -vf "$(burn 'CLIP A' 24000/1001 23.976)" "${V264[@]}" "${A[@]}" -shortest "$OUT/clip-a.mp4"

# clip-b: 1080p 23.976, 20 s, blue field with a sweeping bar, 660 Hz beep every second
"${FF[@]}" -f lavfi -i "color=c=0x1f4e8c:size=1920x1080:rate=24000/1001:duration=20" \
  -f lavfi -i "aevalsrc='0.1*sin(2*PI*660*t)*lt(mod(t\,1)\,0.1)|0.1*sin(2*PI*660*t)*lt(mod(t\,1)\,0.1)':s=48000:d=20" \
  -f lavfi -i "color=c=white:size=60x1080:rate=24000/1001:duration=20" \
  -filter_complex "[2]format=rgba,colorchannelmixer=aa=0.35[bar];[0][bar]overlay=x='mod(t*576\,W)':y=0,$(burn 'CLIP B' 24000/1001 23.976)[v]" \
  -map "[v]" -map 1:a "${V264[@]}" "${A[@]}" -shortest "$OUT/clip-b.mp4"

# clip-c: 720p 29.97, 10 s, different size and rate for mismatched-sequence tests, no audio
"${FF[@]}" -f lavfi -i "testsrc2=size=1280x720:rate=30000/1001:duration=10" \
  -vf "hue=h=120,$(burn 'CLIP C' 30000/1001 29.97)" "${V264[@]}" -an "$OUT/clip-c-720p2997.mp4"

# tone: 5 s, 1 kHz at -20 dBFS, stereo (level and gain tests)
"${FF[@]}" -f lavfi -i "sine=frequency=1000:sample_rate=48000:duration=5" -af "volume=-17dB" -ac 2 -c:a pcm_s16le "$OUT/tone-1k.wav"

# sfx: a short pop and a soft paper-like slide
"${FF[@]}" -f lavfi -i "aevalsrc='0.6*sin(2*PI*180*t)*exp(-t*40)+0.2*(random(0)-0.5)*exp(-t*90)':s=48000:d=0.3" -ac 2 -c:a pcm_s16le "$OUT/sfx-pop.wav"
"${FF[@]}" -f lavfi -i "anoisesrc=color=pink:amplitude=0.5:sample_rate=48000:duration=0.7:seed=7" \
  -af "highpass=f=1200,lowpass=f=6000,afade=t=in:d=0.25,afade=t=out:st=0.35:d=0.35,volume=-6dB" -ac 2 -c:a pcm_s16le "$OUT/sfx-slide.wav"

# lower-third.png: 1920x1080 with transparency
"${FF[@]}" -f lavfi -i "color=c=black@0.0:size=1920x1080,format=rgba" \
  -f lavfi -i "color=c=0x1f4e8c@0.92:size=900x150,format=rgba" -f lavfi -i "color=c=white:size=14x150,format=rgba" -frames:v 1 \
  -filter_complex "[0][1]overlay=120:820:format=auto[x];[x][2]overlay=120:820:format=auto,\
drawtext=fontfile=$FONT:text='Lower Third':fontsize=64:fontcolor=white:x=170:y=842,\
drawtext=fontfile=$FONT:text='demo graphic with alpha':fontsize=36:fontcolor=white@0.85:x=172:y=918" \
  "$OUT/lower-third.png"

# still.jpg: plain 1080p still (image import, still duration tests)
"${FF[@]}" -f lavfi -i "gradients=size=1920x1080:c0=0x2a1a5e:c1=0xe0745a:seed=3:duration=1:speed=0.00001" -frames:v 1 \
  -vf "drawtext=fontfile=$FONT:text='STILL':fontsize=200:fontcolor=white@0.9:x=(w-tw)/2:y=(h-th)/2" -q:v 3 "$OUT/still.jpg"

ls -la "$OUT"
