#!/bin/bash
# Chunked RVM matte -> gray alpha.mkv. Chunks keep peak PNG usage ~1.6GB (disk is tight).
#
# content-engine (Windows, Git Bash): run from the video folder, e.g.
#   bash work/persa-short/videos/<slug>/matte.sh
# The skill is found by walking up to <repo>/.claude/skills/persa-short-editing, and the RVM env
# is <repo>/work/persa-short/rvm_env (made with the signed Python 3.12, see SETUP.md) unless
# PERSA_RVM_ENV points elsewhere. (The original sourced ~/.cache/nextphase/rvm_env and a macOS nvm PATH.)
set -e
cd "$(dirname "$0")"
d="$PWD"; SKD=""; REPO=""
while [ -n "$d" ] && [ "$d" != "/" ]; do
  if [ -d "$d/.claude/skills/persa-short-editing" ]; then SKD="$d/.claude/skills/persa-short-editing"; REPO="$d"; break; fi
  d="$(dirname "$d")"
done
[ -n "$SKD" ] || { echo "matte.sh: cannot find .claude/skills/persa-short-editing above $PWD" >&2; exit 1; }
SK="$SKD/scripts"
RVM="${PERSA_RVM_ENV:-$REPO/work/persa-short/rvm_env}"
if [ -x "$RVM/Scripts/python.exe" ]; then PY="$RVM/Scripts/python.exe"
elif [ -x "$RVM/bin/python" ]; then PY="$RVM/bin/python"
else echo "matte.sh: no RVM env at $RVM (see .claude/skills/persa-short-editing/SETUP.md)" >&2; exit 1; fi

NF=$(ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames -of csv=p=0 assets/recording.mp4)
NF=${NF//$'\r'/}
CH=700
mkdir -p work/alpha_parts
rm -f work/alpha_parts/*.mkv
i=0
for (( s=0; s<NF; s+=CH )); do
  n=$(( NF - s )); [ $n -gt $CH ] && n=$CH
  rm -rf work/frames_rvm; mkdir -p work/frames_rvm
  echo "=== chunk $i  start=$s  frames=$n ==="
  "$PY" "$SK/rvm-matte.py" --src assets/recording.mp4 --out work/frames_rvm \
         --frames "$n" --start "$s" --downsample 0.4
  ffmpeg -v error -y -framerate 30 -i work/frames_rvm/%05d.png \
         -vf "alphaextract,format=gray" -c:v ffv1 -level 3 "work/alpha_parts/p$(printf %02d $i).mkv"
  rm -rf work/frames_rvm
  i=$(( i + 1 ))
done
(cd work/alpha_parts && ls p*.mkv | sed "s|^|file '|;s|$|'|" > list.txt)
ffmpeg -v error -y -f concat -safe 0 -i work/alpha_parts/list.txt -c copy assets/alpha.mkv
echo "DONE alpha.mkv"
ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames -of csv=p=0 assets/alpha.mkv
