# Guía de venta

## A quién venderle

Clínicas y consultorios odontológicos pequeños y medianos, de 1 a 10 sillones, que hoy trabajan con agenda en papel, Excel o un sistema antiguo. Quien decide suele ser el odontólogo dueño; quien más lo usa es la recepcionista.

## El mensaje en una frase

> **Toda tu clínica en una sola pantalla: agenda sin choques, odontograma digital, historia clínica segura y cobros al día, en la computadora y en el celular.**

## Lo que más vende (en este orden)

1. **Oportunidades con WhatsApp.** «Te dice a quién escribir hoy: citas de mañana sin confirmar, cumpleaños, tratamientos aprobados sin cita, pacientes que no vienen hace 6 meses y saldos pendientes. Un toque y el mensaje ya está escrito.» Es dinero recuperado, fácil de demostrar.
2. **Odontograma digital** con pincel, deshacer, símbolos clínicos e historial de versiones.
3. **Agenda sin choques** de horario, con búsqueda de huecos libres.
4. **Créditos en cuotas**: tratamientos financiados, cuotas vencidas y cobro de cuotas.
5. **Cumplimiento legal (LOPDP)**: aviso de privacidad, registro de quién vio cada ficha, exportación de datos. Tranquiliza al dueño.
6. **App móvil**: la ficha, la agenda y la cámara para radiografías, en el bolsillo.

## Demostración de 10 minutos

1. Panel: «Esto es lo primero que ve cada mañana.»
2. Oportunidades: abrir un WhatsApp con el mensaje ya escrito.
3. Agenda: buscar un hueco libre y agendar.
4. Ficha de un paciente: odontograma con pincel, y luego la historia clínica.
5. Cuenta del paciente: cobrar y financiar en cuotas.
6. Celular: la misma ficha en la app.
7. Cierre: «Los datos son tuyos. Respaldo diario. Cumple la LOPDP.»

Para la demo, use una instalación con `seed.py` (datos de demostración). Nunca use la de un cliente.

## Precios: cómo pensarlos

No hay precios fijados. Esta es una estructura habitual en software para clínicas pequeñas:

| Plan | Para quién | Modalidad |
|---|---|---|
| Consultorio | 1 profesional | Suscripción mensual en la nube |
| Clínica | 2 a 5 profesionales | Suscripción mensual en la nube |
| Instalación propia | Clínicas que quieren su servidor | Pago único + mantenimiento anual opcional |

Antes de fijar cifras, compare con los competidores locales y calcule su costo por clínica: servidor, dominio y horas de soporte. Ofrecer 1 mes gratis o una migración de datos incluida baja la barrera de entrada.

## Objeciones frecuentes

- **«¿Factura electrónica?»** — No emite comprobantes del SRI. Se sigue usando el sistema de facturación actual. Ver `LANZAMIENTO.md`.
- **«¿Y si se cae el internet?»** — Con la instalación propia en la red de la clínica, funciona sin internet. En la nube, hace falta conexión.
- **«¿Mis datos?»** — Son de la clínica. Se exportan cuando quiera, y al terminar el contrato se entregan completos.
