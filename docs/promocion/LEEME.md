# Material de promoción

Todo está pensado para vender a **odontólogos que trabajan solos, consultorios de 2 o 3 personas y clínicas**. No lleva emojis ni música con derechos de terceros: la música es original, generada para estos videos.

## Videos

| Archivo | Formato | Para qué |
|---|---|---|
| `video-promocional-horizontal.mp4` | 1920×1080, 43 s | Anuncio principal para YouTube, Facebook, la web y presentaciones |
| `video-promocional-vertical.mp4` | 1080×1920, 43 s | El mismo anuncio para Instagram Reels, TikTok y estados de WhatsApp |
| `teaser-proximamente-horizontal.mp4` | 1920×1080, 20 s | Avance «Próximamente» para generar expectativa antes del lanzamiento |
| `teaser-proximamente-vertical.mp4` | 1080×1920, 20 s | El mismo avance en vertical |
| `tomas-sin-edicion.mp4` | 1920×1080, 4 min 42 s | Todas las tomas reales seguidas, sin edición, para editar a su gusto |
| `tomas/` | Web 1920×1080 · App 1080×2338 | Cada toma por separado (13 de la web y 7 del celular) |
| `escenas/` | PNG | 13 cuadros del anuncio en horizontal y vertical, para publicaciones sueltas o carruseles |

El audio está normalizado a -14 LUFS, el nivel que usan Instagram, TikTok y YouTube, así que no suena ni bajo ni saturado al subirlo.

### Estructura del anuncio (gancho, contenido y llamado a la acción)

| Tiempo | Parte | Qué pasa |
|---|---|---|
| 0–3 s | **Gancho** | «¿Tu consultorio todavía vive en papel?» y se tachan la agenda de papel, el Excel, los chats y los cobros olvidados |
| 3–5 s | **Dolor** | «Citas que se olvidan. Cobros que se pierden. Horas en papeleo.» |
| 5–7,5 s | **Revelación** | Logo y «Tu consulta completa. En una sola app.» |
| 7,5–31,5 s | **Contenido** | 8 funciones con tomas reales: agenda, odontograma, oportunidades por WhatsApp, cartera, finanzas, comprobantes con tu logo, tu marca y la app del celular |
| 31,5–35 s | **Para quién** | Trabajas solo · Consultorio pequeño · Clínica con equipo |
| 35–37,5 s | **Confianza** | Datos protegidos (LOPDP) · Respaldo diario · Web y app móvil · Listo en minutos |
| 37,5–43 s | **Llamado a la acción** | «Agenda tu demo gratis» con un botón que late |

### Tomas

| Toma | Contenido |
|---|---|
| `web-01-ingreso` … `web-13-busqueda` | Ingreso, panel, agenda, ficha del paciente, odontograma, oportunidades, cartera, finanzas (gastos fijos y proyección), estado de cuenta con logo, personalización (cambio de color en vivo), legal y cumplimiento, modo oscuro y búsqueda |
| `app-01-ingreso` … `app-07-oportunidades` | Ingreso, panel, agenda, ficha con odontograma, cartera, finanzas y oportunidades |

## Poner su WhatsApp en el cierre

Los videos terminan con «Escríbenos por WhatsApp». Para poner su número, vuelva a montarlos (tarda unos 15 minutos y no necesita grabar de nuevo):

```bash
cd docs/promocion/fuente
CONTACTO="WhatsApp 099 123 4567" ./armar-todo.sh solo-montaje
```

## Regenerar todo desde cero

`fuente/armar-todo.sh` graba de nuevo las tomas (web y celular), genera la música y monta los cuatro videos. Los requisitos están al inicio del script. Archivos de `fuente/`:

- `tomas-web.mjs` y `tomas-movil.mjs`: el guion de cada toma (clics, escritura y desplazamientos, con un cursor animado).
- `grabadora.mjs`: captura en alta calidad cuadro a cuadro.
- `film.html` y `film.js`: el montaje animado (textos, transiciones, marcos de laptop y celular).
- `render.mjs`: exporta el montaje a video.
- `musica.py`: la música original (120 BPM, con impactos y barridos sincronizados con los cortes).
