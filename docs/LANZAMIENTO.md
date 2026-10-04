# Lista de lanzamiento

Qué está listo en el producto y qué queda en manos del vendedor antes de cobrar a la primera clínica.

## Listo en el producto

- [x] Web, app Android y app de escritorio Linux, con el mismo diseño (claro y oscuro).
- [x] Módulos: pacientes, historia clínica versionada, odontograma, periodontograma, tratamientos y presupuestos, agenda con huecos libres, evoluciones, recetas, consentimientos, documentos, radiografías, caja, finanzas, créditos en cuotas, inventario, laboratorio, reportes y oportunidades con WhatsApp.
- [x] Seguridad:
  - HTTPS automático;
  - el sistema no arranca con configuración insegura;
  - contraseñas con política mínima y cambio obligatorio de la clave temporal;
  - bloqueo tras intentos fallidos;
  - roles y permisos;
  - registro de accesos;
  - contenedores sin privilegios de root;
  - base de datos no expuesta a internet.
- [x] Protección de datos (LOPDP): aviso de privacidad con constancia, autorización de comunicaciones revocable, exportación de datos del paciente, acuerdo de confidencialidad del personal y registros clínicos que no se borran.
- [x] Operación: migraciones y permisos automáticos al actualizar, respaldo diario verificado, recordatorios de citas automáticos.
- [x] Alta de clínica limpia con `nueva_clinica.py`: administrador con clave temporal y catálogo inicial de tratamientos.
- [x] App configurable para cualquier clínica: el servidor se elige en el login.
- [x] Pruebas automáticas: backend y app.

## Pendiente del vendedor (fuera del código)

### Legal y comercial
- [ ] Constituir la empresa o registrarse como persona natural con RUC para facturar las licencias.
- [ ] Hacer revisar por un abogado los textos de `docs/legal/` y los avisos de *Privacidad y legal* del sistema.
- [ ] Elegir nombre comercial y verificar en el SENADI que la marca esté libre. «Sistema Odontológico» es genérico y no se puede registrar como marca.
- [ ] Definir precios. Hay una guía en `docs/VENTAS.md`.
- [ ] Publicar una política de privacidad en una URL (la pide Google Play).

### Infraestructura
- [ ] Contratar el servidor (VPS) y el dominio.
- [ ] Configurar una copia de los respaldos fuera del servidor (por ejemplo, rclone hacia otra nube).
- [ ] Opcional: cuenta de WhatsApp Business Cloud API para recordatorios automáticos.

### App
- [ ] Crear la clave de firma y la cuenta de Google Play. Ver `docs/PUBLICAR_APP.md`.
- [ ] iOS: requiere una Mac y una cuenta de Apple Developer. El código es compatible, pero no se ha compilado ni probado para iPhone.

## Limitaciones que conviene decir al vender

- **No emite facturas electrónicas del SRI.** Registra cargos, pagos y créditos para la gestión interna; la clínica factura con su sistema autorizado. Integrar la facturación electrónica es la mejora más pedida y conviene planificarla.
- Los recordatorios automáticos por WhatsApp requieren la cuenta de Meta. Sin ella, los botones de WhatsApp manuales funcionan igual.
- El horario para buscar huecos libres es de lunes a sábado, de 08:00 a 19:00. No hay horario por profesional.
