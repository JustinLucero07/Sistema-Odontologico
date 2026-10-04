# Material de promoción

| Archivo | Uso |
|---|---|
| `video-promocional-horizontal.mp4` | 1920×1080, 40 s. Para YouTube, Facebook, la web y presentaciones |
| `video-promocional-vertical.mp4` | 1080×1920, 40 s. Para Instagram Reels, TikTok y estados de WhatsApp |
| `escenas/` | Cada escena como imagen, para publicaciones sueltas o un carrusel |
| `capturas/` | Capturas reales del sistema con datos de demostración |

La música es una base suave generada para este video: no tiene derechos de autor de terceros. En Instagram o TikTok puede reemplazarla por una canción de la biblioteca de la plataforma.

## Cambiar el cierre del video (su WhatsApp o su web)

El cierre dice «Escríbenos y agenda tu demo gratuita». Para poner su contacto:

```bash
cd docs/promocion/fuente
CONTACTO="WhatsApp 099 123 4567" CHROME=~/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome node escenas.mjs
./armar.sh h && ./armar.sh v
for F in h v; do ffmpeg -y -i sin_audio_$F.mp4 -i musica.wav -c:v copy -c:a aac -b:a 160k -t 40.6 promo_$F.mp4; done
```

Requiere Node, ffmpeg y Playwright (ya instalados en esta máquina).
