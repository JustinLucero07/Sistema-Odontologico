# Locución del video de lanzamiento (52 s)

Voz cálida y segura, ritmo ágil pero sin correr. Español neutro latinoamericano
(o ecuatoriano). Cada frase entra en el segundo indicado y debe terminar antes
del siguiente.

| Segundo | Escena en pantalla | Texto de la voz |
|---|---|---|
| 0,8 | Logo | Toda tu consulta dental, en un solo sistema. |
| 5,5 | El sistema en la computadora | Agenda, fichas, facturación electrónica y finanzas. Todo conectado. |
| 10,3 | Agenda | Agenda sin choques, con recordatorios automáticos. |
| 13,3 | Ficha | La ficha completa de cada paciente. |
| 16,3 | Odontograma | Odontograma digital, pieza por pieza. |
| 19,3 | Facturación | Facturas electrónicas autorizadas por el SRI, en segundos. |
| 22,3 | Consentimientos | Consentimientos firmados en la pantalla… o desde el celular del paciente. |
| 25,3 | Finanzas | Y tus cobros y finanzas, siempre claros. |
| 28,4 | App: ingreso | Una app que da gusto usar. |
| 31,5 | App: navegación | Todo a un toque, en tu bolsillo. |
| 34,7 | App: sin internet | Y sigue funcionando, incluso sin internet. |
| 38,0 | Computadora, tablet y celular | En la computadora, la tablet o el celular: los mismos datos, donde estés. |
| 43,4 | Beneficios | Hecho para la consulta dental en Ecuador. |
| 47,8 | Cierre | Sistema Odontológico. Solicita tu demostración. |

## Cómo grabarla y unirla

1. Graba la voz en un solo archivo de 52 segundos que empiece en el segundo 0
   (con el celular o un micrófono, en un cuarto sin eco), siguiendo la tabla.
   También sirve una voz generada por un servicio de voz con IA.
2. Guárdala como `docs/promocion/fuente/voz-lanzamiento.wav` (o .mp3).
3. Ejecuta:

       cd docs/promocion/fuente
       ./mezclar-voz.sh voz-lanzamiento.wav

   Crea `lanzamiento-horizontal-con-voz.mp4` y `lanzamiento-vertical-con-voz.mp4`:
   la música baja sola cada vez que habla la voz y el volumen final queda listo
   para redes (−14 LUFS).

## Generarla con una voz de IA (sin grabar)

Sirve cualquier servicio de texto a voz en español (por ejemplo ElevenLabs,
Murf o la voz de Canva/CapCut).

1. **Elige o diseña la voz** con esta descripción (en ElevenLabs:
   *Voice Design*; en otros, elige la voz que más se parezca):

   > Voz de locutor publicitario latinoamericano, adulto de 30 a 40 años,
   > cálida, cercana y segura, con sonrisa en la voz. Ritmo ágil pero claro,
   > sin exagerar ni sonar a vendedor. Calidad de estudio, sin eco ni música.
   > Pronunciación neutra latinoamericana, natural para Ecuador.

2. **Genera cada frase por separado** (las 14 de la tabla, en orden) y
   descárgalas con los nombres `01.mp3`, `02.mp3` … `14.mp3`. Recomendaciones:
   estabilidad media (≈ 45 %), velocidad normal o 1,05×, y que ninguna frase
   dure más que su espacio en la tabla (si una se alarga, el script la acelera
   un poco hasta 1,2× y avisa si aun así no entra).

3. Copia las 14 frases a `docs/promocion/fuente/voz/` y ejecuta:

       cd docs/promocion/fuente
       ./armar-voz.sh

   Coloca cada frase en su segundo exacto, arma `voz-lanzamiento.wav` y crea
   `lanzamiento-horizontal-con-voz.mp4` y `lanzamiento-vertical-con-voz.mp4`
   con la música bajando sola cuando habla la voz.
