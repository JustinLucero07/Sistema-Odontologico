#!/bin/bash
# armar.sh h|v  → video con movimiento suave y transiciones
set -e
F=$1
if [ "$F" = h ]; then W=1920; H=1080; else W=1080; H=1920; fi
FPS=30; T=0.7
mkdir -p clips/$F
DUR=(3.6 4.2 4.4 4.4 4.4 4.2 4.6 4.4 4.4 4.0 5.0)
i=0
for img in escenas/$F/*.png; do
  d=${DUR[$i]}; frames=$(python3 -c "print(int($d*$FPS))")
  # Acercamiento lento (Ken Burns) desde la imagen a 2x para que se vea nítido.
  ffmpeg -y -loglevel error -loop 1 -i "$img" -t $d -vf \
   "zoompan=z='1+0.045*on/$frames':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=$frames:s=${W}x${H}:fps=$FPS,format=yuv420p" \
   -c:v libx264 -preset slow -crf 18 -r $FPS clips/$F/$(printf %02d $i).mp4
  i=$((i+1))
done
# Encadenar con transiciones
inputs=(); filter=""; offset=0; prev="[0:v]"
n=${#DUR[@]}
for ((k=0;k<n;k++)); do inputs+=(-i clips/$F/$(printf %02d $k).mp4); done
acc=${DUR[0]}
for ((k=1;k<n;k++)); do
  off=$(python3 -c "print(round($acc-$T*$k,3))")
  trans=$([ $((k%3)) -eq 0 ] && echo smoothleft || echo fade)
  filter+="${prev}[$k:v]xfade=transition=$trans:duration=$T:offset=$off[v$k];"
  prev="[v$k]"; acc=$(python3 -c "print($acc+${DUR[$k]})")
done
total=$(python3 -c "print(round($acc-$T*($n-1),2))")
filter+="${prev}fade=t=in:st=0:d=0.5,fade=t=out:st=$(python3 -c "print($total-0.8)"):d=0.8[vout]"
ffmpeg -y -loglevel error "${inputs[@]}" -filter_complex "$filter" -map "[vout]" -c:v libx264 -preset slow -crf 19 -pix_fmt yuv420p -movflags +faststart -r $FPS sin_audio_$F.mp4
echo "$F total ${total}s"
