# Material de promoción

Todo está pensado para vender a **odontólogos que trabajan solos, consultorios de 2 o 3 personas y clínicas**. No lleva emojis ni música con derechos de terceros: la música es original, generada para estos videos.

**Estilo:** anuncio para redes con bloques de color sólido que cambian al ritmo (sin degradados), tipografía grande con resaltador amarillo y las pantallas reales **completas**: la web en una laptop y la app en un celular, lado a lado. Música original estilo house pop (120 BPM) con gancho, drop y segundo drop en el cierre.

## Campaña principal (la más profesional)

| Archivo | Formato | Para qué |
|---|---|---|
| `campana-horizontal.mp4` | 1920×1080, 46 s | YouTube, página web, presentaciones comerciales |
| `campana-vertical.mp4` | 1080×1920, 46 s | Instagram y Facebook Reels, TikTok, estados de WhatsApp |

Estilo premium: fondo oscuro con luz ambiental sutil, laptop y celular con reflejo, acercamientos suaves de cámara y tipografía sobria. Todo lo que se ve son pantallas reales del sistema; no hay funciones inventadas. Cada formato tiene su propia composición: en horizontal, la laptop protagoniza con acercamientos a lo importante; en vertical, la web se ve completa arriba y el celular o una lupa abajo, dentro de las zonas seguras de Reels y TikTok.

| Tiempo | Escena |
|---|---|
| 0–5 s | Apertura: línea de luz, logo y «Toda tu consulta dental. Un solo sistema.» |
| 5–10 s | Presentación: la laptop se enciende con el panel real |
| 10–31 s | 7 funciones: agenda, odontograma, oportunidades, cartera, finanzas, comprobantes con logo y personalización |
| 31–37 s | Web y app móvil con los mismos datos (el mismo odontograma y la misma cartera en los dos) |
| 37–41 s | Beneficios reales |
| 41–46 s | Cierre: logo y «Solicita una demostración» |

Para agregar su contacto al cierre (solo aparece si lo indica):

```bash
cd docs/promocion/fuente
CONTACTO="WhatsApp 099 123 4567" ./armar-todo.sh solo-montaje
```

## Otros videos

| Archivo | Formato | Para qué |
|---|---|---|
| `video-promocional-horizontal.mp4` | 1920×1080, 40 s | Anuncio principal para YouTube, Facebook, la web y presentaciones |
| `video-promocional-vertical.mp4` | 1080×1920, 40 s | El mismo anuncio para Instagram Reels, TikTok y estados de WhatsApp |
| `teaser-proximamente-horizontal.mp4` | 1920×1080, 20 s | Avance «Próximamente» para generar expectativa antes del lanzamiento |
| `teaser-proximamente-vertical.mp4` | 1080×1920, 20 s | El mismo avance en vertical |
| `tomas-sin-edicion.mp4` | 1920×1080, 4 min 42 s | Todas las tomas reales seguidas, sin edición, para editar a su gusto |
| `tomas/` | Web 1920×1080 · App 1080×2338 | Cada toma por separado (13 de la web y 7 del celular) |
| `escenas/` | PNG | 13 cuadros del anuncio en horizontal y vertical, para publicaciones sueltas o carruseles |

El audio está normalizado a -14 LUFS, el nivel que usan Instagram, TikTok y YouTube, así que no suena ni bajo ni saturado al subirlo.

### Estructura del anuncio (gancho, contenido y llamado a la acción)

| Tiempo | Parte | Qué pasa |
|---|---|---|
| 0–3 s | **Gancho** | Tres preguntas que golpean al ritmo: «¿Agenda en papel?», «¿Cobros olvidados?», «¿Pacientes que no vuelven?» |
| 3–4 s | **Giro** | «Hay una forma mejor.» |
| 4–6 s | **Revelación (drop)** | Logo y «Tu consultorio completo, en una sola app» |
| 6–30 s | **Contenido** | 8 funciones de 3 s cada una con la web y la app reales: agenda, odontograma, oportunidades, cartera, finanzas, comprobantes con logo, tu marca y legal |
| 30–33 s | **Para quién** | ¿Trabajas solo? · ¿Son dos o tres? · ¿Tienes una clínica? |
| 33–34 s | **Confianza** | Es para ti: datos protegidos, respaldo diario, web y celular, listo en minutos |
| 34–40 s | **Llamado a la acción (segundo drop)** | «Agenda tu demo gratis» con el botón de contacto |

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
- `musica.py`: la música original (house pop, 120 BPM, con drops y barridos sincronizados con los cortes).
