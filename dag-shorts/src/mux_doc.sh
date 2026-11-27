#!/bin/bash
# Belgesel versiyon: parçaları birleştir + ses -> final
set -e; cd "$(dirname "$0")/.."
printf "file 'doc0.mp4'\nfile 'doc1.mp4'\nfile 'doc2.mp4'\nfile 'doc3.mp4'\n" > build/docparts.txt
ffmpeg -y -v error -f concat -safe 0 -i build/docparts.txt -i build/audio_doc.wav -map 0:v -map 1:a \
  -c:v libx264 -preset slow -crf 22 -maxrate 12M -bufsize 24M -pix_fmt yuv420p -c:a aac -b:a 256k -shortest -movflags +faststart \
  turkiyenin-en-yuksek-10-dagi-belgesel.mp4
ffprobe -v error -show_entries format=duration,size -of default=nw=1 turkiyenin-en-yuksek-10-dagi-belgesel.mp4
