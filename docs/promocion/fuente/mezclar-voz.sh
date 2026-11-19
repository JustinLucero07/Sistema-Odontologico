#!/usr/bin/env bash
# Une una locución al video de lanzamiento: la música baja sola mientras habla
# la voz (compresión por cadena lateral) y el resultado queda a −14 LUFS.
#   ./mezclar-voz.sh voz-lanzamiento.wav
set -euo pipefail
cd "$(dirname "$0")"
VOZ="${1:?Indique el archivo de voz (wav o mp3)}"
for f in horizontal vertical; do
  ENTRADA="../lanzamiento-$f.mp4"
  [ -f "$ENTRADA" ] || { echo "Falta $ENTRADA"; exit 1; }
  ffmpeg -loglevel error -y -i "$ENTRADA" -i "$VOZ" -filter_complex "
    [1:a]aformat=sample_rates=48000:channel_layouts=stereo,highpass=f=80,acompressor=threshold=-20dB:ratio=3:attack=5:release=120,volume=1.6,asplit=2[voz][llave];
    [0:a]aformat=sample_rates=48000:channel_layouts=stereo[musica];
    [musica][llave]sidechaincompress=threshold=0.02:ratio=10:attack=25:release=450:makeup=1[base];
    [base][voz]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-14:TP=-1.2:LRA=9[a]" \
    -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 192k -ar 48000 -movflags +faststart "../lanzamiento-$f-con-voz.mp4"
  echo "✔ lanzamiento-$f-con-voz.mp4"
done
