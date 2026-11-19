#!/usr/bin/env bash
# Arma la locución del video de lanzamiento a partir de 14 frases sueltas
# (generadas con un servicio de voz con IA o grabadas) y la une a los videos.
#
#   Pon las frases en docs/promocion/fuente/voz/ con nombres 01.mp3 … 14.mp3
#   (sirven .mp3, .wav o .m4a) y ejecuta:   ./armar-voz.sh
#
# Cada frase entra en su segundo exacto. Si alguna dura más que su espacio,
# se acelera un poco (hasta 1,2×) para que no pise a la siguiente.
set -euo pipefail
cd "$(dirname "$0")"

INICIOS=(0.8 5.5 10.3 13.3 16.3 19.3 22.3 25.3 28.4 31.5 34.7 38.0 43.4 47.8)
FIN_TOTAL=51.6
ENTRADAS=(); FILTROS=""; MEZCLA=""; n=0

for i in $(seq 0 13); do
  num=$(printf "%02d" $((i + 1)))
  archivo=$(ls voz/$num.* 2>/dev/null | head -1 || true)
  [ -n "$archivo" ] || { echo "Falta la frase voz/$num (mp3, wav o m4a)"; exit 1; }
  inicio=${INICIOS[$i]}
  if [ $i -lt 13 ]; then fin=${INICIOS[$((i + 1))]}; else fin=$FIN_TOTAL; fi
  dur=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$archivo")
  espacio=$(python3 -c "print(round($fin - $inicio - 0.15, 3))")
  tempo=$(python3 -c "d=$dur; e=$espacio; print(round(min(max(d/e,1.0),1.2),4))")
  if python3 -c "import sys; sys.exit(0 if $dur/$espacio > 1.2 else 1)"; then
    echo "Aviso: la frase $num dura ${dur}s y su espacio es ${espacio}s; aun acelerada se pasará un poco. Conviene generarla más corta o más rápida."
  fi
  ms=$(python3 -c "print(int($inicio * 1000))")
  ENTRADAS+=(-i "$archivo")
  FILTROS+="[$n:a]aformat=sample_rates=48000:channel_layouts=stereo,silenceremove=start_periods=1:start_threshold=-50dB,atempo=$tempo,adelay=${ms}|${ms}[f$n];"
  MEZCLA+="[f$n]"
  n=$((n + 1))
done

ffmpeg -loglevel error -y "${ENTRADAS[@]}" -filter_complex \
  "${FILTROS}${MEZCLA}amix=inputs=$n:duration=longest:normalize=0,apad=whole_dur=52[v]" \
  -map "[v]" -t 52 -ar 48000 voz-lanzamiento.wav
echo "✔ voz-lanzamiento.wav (52 s)"

./mezclar-voz.sh voz-lanzamiento.wav
