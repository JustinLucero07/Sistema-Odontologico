# Cumplimiento legal

Este documento explica qué obligaciones legales cubre el sistema y cuáles quedan a cargo de la clínica. Está pensado para el dueño o administrador de cada clínica que lo use, y para quien lo instale.

> **Importante.** El sistema ofrece las herramientas para cumplir, pero no sustituye la asesoría legal. Antes de usar los textos legales con pacientes, un abogado de la clínica debe revisarlos. Las referencias a normas corresponden al Ecuador; en otro país hay que adaptarlas.

## Marco aplicable

- **Ley Orgánica de Protección de Datos Personales (LOPDP)** y su reglamento. Los datos de salud son *categoría especial* y exigen más cuidado: informar al paciente, limitar el acceso, garantizar la seguridad y atender sus derechos.
- **Normativa sanitaria sobre la historia clínica y la información confidencial en salud** del Ministerio de Salud Pública. Obliga a conservar la historia clínica, a no alterarla y a guardar la confidencialidad.
- **Normas sobre recetas médicas y consentimiento informado.**
- **Normativa tributaria del SRI**, para la facturación.

## Lo que ya hace el sistema

| Obligación | Cómo se cumple | Dónde |
|---|---|---|
| Informar al paciente cómo se tratan sus datos | Al registrar un paciente es obligatorio marcar que se le informó. Queda constancia con la fecha, la versión del aviso, el método y quién lo registró. El aviso se imprime para que lo firme. | Alta de paciente · Ficha › Protección de datos |
| Autorización para mensajes | La autorización es opcional y aparte del aviso. Se puede retirar en cualquier momento, y al retirarla el sistema deja de enviar mensajes, recordatorios incluidos. | Ficha › Protección de datos |
| Menores de edad | Si el paciente es menor, el sistema exige el nombre de su representante legal. El consentimiento informado impreso pide la firma del representante. | Alta · Ficha · Consentimientos |
| Derecho de acceso y portabilidad | Exporta en un solo archivo todos los datos del paciente en formato legible por máquina. La descarga queda registrada. | Ficha › Exportar sus datos (permiso `patients:export`) |
| Rectificación | Los datos personales se editan desde la ficha, y cada cambio queda auditado. | Ficha › Editar datos |
| Conservación e integridad de la historia clínica | Los registros clínicos no se borran. Los diagnósticos y recetas erróneos se *anulan* con un motivo y siguen a la vista. Las correcciones de evoluciones guardan el texto anterior. Dar de baja a un paciente no borra su historia. | Toda la historia clínica |
| Confidencialidad del personal | Cada usuario acepta un acuerdo de confidencialidad antes de trabajar. Si el texto cambia, se le pide aceptarlo de nuevo. | Al iniciar sesión |
| Registro de accesos | Cada apertura de una ficha queda registrada con usuario, fecha y hora. | Ficha › Quién vio esta ficha (permiso `audit:read`) |
| Acceso mínimo necesario | Los roles y permisos limitan qué ve cada persona. Por ejemplo, contabilidad no ve la historia clínica. | Configuración › Roles y permisos |
| Seguridad | Contraseñas cifradas; bloqueo tras intentos fallidos; sesiones que se cierran al cambiar la contraseña o desactivar al usuario; cabeceras de seguridad; copias de respaldo. | Ver `OPERACIONES.md` |
| Receta válida | Exige al profesional que prescribe. La receta impresa lleva la clínica, el paciente con su cédula y edad, los medicamentos con dosis, frecuencia y duración, y el nombre, registro profesional y espacio de firma del prescriptor. | Historia clínica › Recetas |
| Consentimiento informado | Guarda el texto exacto que firmó el paciente, aunque la plantilla cambie después. Se imprime con espacio para las firmas. | Historia clínica › Consentimientos |

## Lo que tiene que hacer la clínica

1. **Completar sus datos** en *Configuración › Datos de la clínica*: razón social, RUC, dirección, teléfono y un **correo para ejercer derechos**. El aviso de privacidad los toma de ahí; sin ellos queda incompleto.
2. **Revisar los textos con su abogado.** Están en *Privacidad y legal*, en el menú de usuario. Si se cambian, hay que subir la versión en `backend/app/modules/privacy/constants.py`: el sistema volverá a pedir la aceptación al personal y marcará los avisos entregados con la versión anterior.
3. **Entregar el aviso y guardar la copia firmada.** El sistema registra la constancia; el papel firmado debe archivarse o subirse a *Documentos* del paciente.
4. **Evaluar con el asesor legal si debe designar un delegado de protección de datos** y si debe hacer algún registro ante la Superintendencia de Protección de Datos Personales.
5. **Firmar un contrato de encargo** con quien aloje el sistema (el servidor o la nube). Si los datos se guardan fuera del Ecuador, revisar las reglas de transferencia internacional.
6. **Atender las solicitudes de los pacientes** dentro de los plazos legales. La exportación y la edición de datos ya están en el sistema.
7. **Ante un incidente de seguridad** (robo de un equipo, acceso indebido, filtración), notificar a la Superintendencia y, si corresponde, a los pacientes afectados, dentro del plazo del artículo 43 de la LOPDP. El registro de accesos ayuda a saber qué se vio y quién lo vio.
8. **Conservar la historia clínica** durante el plazo vigente de la normativa sanitaria. El sistema no la borra; las copias de respaldo deben conservarse de acuerdo con ese plazo.
9. **Facturar con su propio sistema autorizado por el SRI.** Este sistema registra cargos, pagos y presupuestos para la gestión interna, pero **no emite comprobantes electrónicos**. Por eso sus documentos dicen «Total de cargos» y el presupuesto aclara que no es un comprobante de venta.
10. **Mantener los datos del personal al día:** el registro profesional de cada profesional (aparece en las recetas) y desactivar de inmediato a quien deje la clínica.

## Para quien mantenga el código

- Versiones de los textos: `backend/app/modules/privacy/constants.py`.
- Textos: `frontend/src/app/shared/legal/legal-texts.ts`. La página y el documento impreso usan la misma fuente.
- La exportación recorre el esquema de la base de datos: toda tabla nueva con `patient_id` y `clinic_id` entra sola, igual que sus tablas hijas directas. Las credenciales (`token_hash`, `hashed_password`) y `clinic_id` nunca salen.
- Pruebas: `backend/tests/test_privacy.py`, además de los casos de recetas en `test_clinical_records.py`.
