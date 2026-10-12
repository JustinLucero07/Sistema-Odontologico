#!/usr/bin/env bash
# Regenera todo el material de video desde cero.
#
#   ./armar-todo.sh                      # todo, con el cierre «Escríbenos por WhatsApp»
#   CONTACTO="WhatsApp 099 123 4567" ./armar-todo.sh solo-montaje   # solo re-montar con su contacto
#
# Requisitos para grabar las tomas (no hacen falta con «solo-montaje»):
#   - backend en http://localhost:8000 (con datos de demostración: seed.py)
#   - web en http://localhost:4200 (ng serve)
#   - app del celular compilada para web y servida en :5050:
#       cd mobile && flutter build web --release --dart-define=API_BASE=http://localhost:8000
#       cd build/web && python3 -m http.server 5050
#     (y CORS_ORIGINS del backend debe incluir http://localhost:5050)
# Herramientas: Node, ffmpeg, Python 3 con numpy y Playwright (Chromium).
set -euo pipefail
cd "$(dirname "$0")"
export CHROME="${CHROME:-$HOME/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome}"
CONTACTO="${CONTACTO:-Escríbenos por WhatsApp}"
DEST=..

if [ "${1:-}" != "solo-montaje" ]; then
  echo "1/5 Grabando tomas web y del celular…"
  mkdir -p tomas
  node tomas-web.mjs
  node tomas-movil.mjs
  cp tomas/*.mp4 "$DEST/tomas/"
fi
[ -d tomas ] || { mkdir -p tomas; cp "$DEST"/tomas/*.mp4 tomas/; }

echo "2/5 Música original…"
python3 musica.py anuncio
python3 musica.py teaser

echo "3/5 Cuadros de las tomas…"
rm -rf cuadros; mkdir -p cuadros
ls tomas/*.mp4 | xargs -P 3 -I{} bash -c 'n=$(basename {} .mp4); mkdir -p cuadros/$n; case $n in web*) S=1440:810;; *) S=720:1558;; esac; ffmpeg -loglevel error -threads 2 -y -i {} -vf "scale=$S:flags=lanczos" -q:v 3 cuadros/$n/%05d.jpg'

echo "4/5 Montaje (unos 15 minutos)…"
python3 -m http.server 5077 >/dev/null 2>&1 & SRV=$!
trap 'kill $SRV' EXIT
sleep 1
for v in anuncio teaser; do for f in h v; do node render.mjs $v $f --contacto "$CONTACTO"; done; done

echo "5/5 Audio y exportación…"
nombre() { case "$1-$2" in anuncio-h) echo video-promocional-horizontal;; anuncio-v) echo video-promocional-vertical;; teaser-h) echo teaser-proximamente-horizontal;; teaser-v) echo teaser-proximamente-vertical;; esac; }
for v in anuncio teaser; do for f in h v; do
  ffmpeg -loglevel error -y -i $v-$f-sin-audio.mp4 -i $v.wav -map 0:v -map 1:a -c:v copy \
    -af "loudnorm=I=-14:TP=-1.2:LRA=9" -c:a aac -b:a 192k -ar 48000 -shortest -movflags +faststart "$DEST/$(nombre $v $f).mp4"
done; done
rm -rf cuadros *-sin-audio.mp4
echo "Listo: videos en docs/promocion/"
