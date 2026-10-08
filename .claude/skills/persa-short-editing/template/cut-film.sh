#!/bin/bash
# cut-film.sh ID SS TO CX CY CW CH TOP  -> src/clips/ID.mp4 1080x1920@30
# sharp crop fitted to width 1080 at y=TOP, over the film's OWN clean ground:
# its top 60px strip stretched to full frame (no ghost of the card).  TOP=full -> plain 9:16 crop.
set -e
cd "$(dirname "$0")"; mkdir -p src/clips
ID=$1 SS=$2 TO=$3 CX=$4 CY=$5 CW=$6 CH=$7 TOP=$8 SP=${9:-1}
if [ "$TOP" = full ]; then
  FC="[0:v]crop=$CW:$CH:$CX:$CY,scale=1080:1920:flags=lanczos"
else
  FC="[0:v]split[a][b];[a]crop=1920:60:0:0,scale=1080:1920,gblur=sigma=30[bg];[b]crop=$CW:$CH:$CX:$CY,scale=1080:-2:flags=lanczos,format=rgba,geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='255*min(1,min(min(X,W-1-X),min(Y,H-1-Y))/60)'[fg];[bg][fg]overlay=0:$TOP"
fi
FC="$FC,setpts=$SP*PTS,fps=30,format=yuv420p"
ffmpeg -v error -y -ss $SS -to $TO -i src/film/film.mp4 -filter_complex "$FC" -an -c:v libx264 -crf 18 -preset medium src/clips/$ID.mp4
echo "$ID done $(ffprobe -v error -show_entries format=duration -of csv=p=0 src/clips/$ID.mp4)s"
