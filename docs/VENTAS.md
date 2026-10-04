# Guía de venta

## A quién venderle

A **cualquier práctica dental**, desde la más pequeña:

| Perfil | Qué le importa | Qué mostrarle primero |
|---|---|---|
| **Odontólogo independiente** (1 persona, a veces sin recepcionista) | Ahorrar tiempo, que no se le olviden citas ni cobros, verse profesional | La app en el celular, recordatorios y Oportunidades por WhatsApp, recetas impresas con su registro |
| **Consultorio de 2 o 3 odontólogos** que comparten espacio | No pisarse la agenda, saber quién cobró qué | Agenda por profesional sin choques, caja del día, reportes por profesional |
| **Clínica con equipo** (recepción, varios sillones) | Control, permisos, finanzas | Roles y permisos, finanzas, créditos, inventario y laboratorio |

Muchos hoy trabajan con agenda en papel, WhatsApp y Excel. El sistema no obliga a usar todo: el odontólogo independiente puede quedarse con agenda, fichas, odontograma y cobros, y el resto queda disponible para cuando crezca.

Para un consultorio de una persona, cree la cuenta con `--odontologo` (ver `INSTALACION_PRODUCCION.md`): el odontólogo es a la vez administrador y profesional, y puede agendar desde el primer minuto.

## El mensaje en una frase

> **Tu consultorio o tu clínica en una sola pantalla: agenda sin choques, odontograma digital, historia clínica segura y cobros al día, en la computadora y en el celular.**

Para el odontólogo independiente, en una frase:

> **Todo tu consultorio en el celular: tus citas, tus pacientes y tus cobros, sin papeles.**

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

No hay precios fijados. Esta es una estructura habitual en software para consultorios y clínicas pequeñas. Conviene que el plan de un solo odontólogo sea claramente accesible: es el cliente más numeroso.

| Plan | Para quién | Modalidad |
|---|---|---|
| Independiente | 1 odontólogo | Suscripción mensual en la nube, el precio más bajo |
| Consultorio | 2 o 3 odontólogos | Suscripción mensual en la nube |
| Clínica | 4 o más profesionales y personal | Suscripción mensual en la nube |
| Instalación propia | Clínicas que quieren su servidor | Pago único + mantenimiento anual opcional |

Antes de fijar cifras, compare con los competidores locales y calcule su costo por cliente: servidor, dominio y horas de soporte. Varios consultorios pequeños pueden compartir un mismo servidor (cada uno con sus datos aislados), lo que abarata el plan independiente. Ofrecer 1 mes gratis o una migración de datos incluida baja la barrera de entrada.

## Objeciones frecuentes

- **«¿Factura electrónica?»** — No emite comprobantes del SRI. Se sigue usando el sistema de facturación actual. Ver `LANZAMIENTO.md`.
- **«Soy solo yo, ¿no es demasiado sistema?»** — Use solo lo que necesite: agenda, fichas, odontograma y cobros. Lo demás no estorba y queda para cuando crezca.
- **«No tengo recepcionista.»** — Por eso está la app: agenda, confirma por WhatsApp y cobra desde el celular, entre paciente y paciente.
- **«¿Y si se cae el internet?»** — Con la instalación propia en la red del consultorio, funciona sin internet. En la nube, hace falta conexión.
- **«¿Mis datos?»** — Son del consultorio o la clínica. Se exportan cuando quiera, y al terminar el contrato se entregan completos.
