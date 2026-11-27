#!/bin/bash
# Parçaları birleştir + sesi ekle -> final video
set -e; cd "$(dirname "$0")/.."
printf "file 'part0.mp4'\nfile 'part1.mp4'\nfile 'part2.mp4'\n" > build/parts.txt
ffmpeg -y -v error -f concat -safe 0 -i build/parts.txt -i build/audio_mix.wav \
  -map 0:v -map 1:a -c:v copy -c:a aac -b:a 256k -shortest -movflags +faststart turkiyenin-en-yuksek-10-dagi.mp4
ffprobe -v error -show_entries format=duration,size -of default=nw=1 turkiyenin-en-yuksek-10-dagi.mp4
