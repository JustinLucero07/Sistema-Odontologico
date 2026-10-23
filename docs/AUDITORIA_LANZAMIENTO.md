# Auditoría previa al lanzamiento comercial

**Fecha:** 23 de octubre de 2026 · **Alcance:** backend (FastAPI), web (Angular), app móvil (Flutter), base de datos y migraciones, despliegue Docker, respaldos, seguridad y requisitos de Ecuador.

**Criterio:** solo se marca algo como verificado si se ejecutó y se vio el resultado. Lo que no se pudo comprobar dice **NO VERIFICADO**.

## Veredicto

**Listo para un piloto controlado con 1 a 3 consultorios o clínicas, con soporte cercano.** Todavía **no** para venta masiva sin antes resolver los puntos de la sección «Pendiente antes de vender a escala».

Lo esencial para manejar información clínica real está verificado:

- separación total entre clínicas;
- ninguna ruta privada responde sin sesión;
- instalación desde cero;
- actualización sin pérdida de datos;
- respaldo y restauración;
- dependencias sin vulnerabilidades conocidas.

Lo que falta es sobre todo operación comercial: facturación electrónica del SRI, monitoreo, respaldos fuera del servidor automatizados y revisión legal de los textos.

## 1. Tecnologías y versiones (verificado en el repositorio)

| Parte | Tecnología |
|---|---|
| Backend | Python 3.12, FastAPI 0.161.1 (Starlette 1.9.0), SQLAlchemy 2.0 async, PostgreSQL 16, Alembic, Redis, PyJWT 2.15.1, Argon2 |
| Web | Angular 18.2, TypeScript 5.5, Angular Material |
| App móvil | Flutter (Dart 3.12), Riverpod, Dio; Android e iOS en el proyecto |
| Despliegue | Docker Compose: Caddy (HTTPS automático), backend, frontend (nginx), PostgreSQL, Redis, recordatorios, respaldos diarios |
| Base de datos | 23 migraciones encadenadas, cabeza `3f5b22a0c21a` |

## 2. Resultado de las verificaciones

| # | Qué se verificó | Cómo | Resultado |
|---|---|---|---|
| 1 | Pruebas automáticas del backend | `cd backend && .venv/bin/pytest -q` | **224 pasan**, 0 fallan |
| 2 | Pruebas de la app móvil | `cd mobile && flutter test` | **40 pasan** |
| 3 | Análisis estático de la app | `flutter analyze` | Sin problemas |
| 4 | Compilación web de producción | `ng build` | Correcta |
| 5 | Compilación Android | `flutter build apk --debug` | Correcta (APK generado) |
| 6 | **Aislamiento entre clínicas** | Prueba nueva `test_aislamiento_clinicas.py`: la clínica B intenta leer, editar, anular y borrar los datos de A en **108 combinaciones de ruta y método** | Todas rechazadas; ningún listado de B muestra datos de A; los datos de A quedan idénticos |
| 7 | Acceso sin sesión | La misma prueba llama a cada ruta de la API sin token | Solo responden las públicas: ingreso, renovación, salida, salud y portal del paciente por enlace |
| 8 | Instalación desde cero | Base vacía, `alembic upgrade head`, `alembic check`, `sync_permissions.py`, `nueva_clinica.py` | Correcta; las 23 migraciones aplican y el modelo coincide |
| 9 | Índices por clínica | Consulta al catálogo de PostgreSQL | Todas las tablas con `clinic_id` tienen índice |
| 10 | Imágenes Docker de producción | `docker compose build` y versiones dentro de la imagen | Correcto |
| 11 | **Actualización con datos existentes** | Stack de producción con datos del 11 de octubre, levantado con las imágenes nuevas | Migración pendiente aplicada sola; datos e ingreso intactos |
| 12 | **Respaldo y restauración** | `odonto respaldar`, cambio posterior, `pg_restore` | El cambio posterior desaparece al restaurar |
| 13 | Encabezados de seguridad en producción | `curl -I https://localhost` | HSTS, X-Frame-Options, CSP y nosniff presentes |
| 14 | Web bajo la política de seguridad (CSP) | Recorrido automático de 14 pantallas e impresión | 0 violaciones, 0 errores en consola |
| 15 | Vulnerabilidades en dependencias | `pip-audit -r backend/requirements.txt` | **0 conocidas** (había 52; ver 3.2) |
| 16 | Rendimiento con volumen | 5.000 pacientes, 30.000 citas, 10.000 cargos y 10.000 cobros; 10 peticiones simultáneas | Ver sección 4 |
| 17 | Recuperar clave del único administrador | `restablecer_clave.py` sobre un usuario real | Entra con la clave temporal, se obliga el cambio y queda en la auditoría |

## 3. Problemas encontrados y corregidos durante la auditoría

### 3.1 Seguridad: imágenes con código (XSS almacenado) — CORREGIDO, grave

El módulo de imágenes aceptaba cualquier archivo que el navegador declarara como `image/*`, incluido SVG, y lo mostraba en el mismo dominio del sistema. Un SVG con un script podía ejecutarse en la sesión de quien lo abriera.

**Ahora:**

- El tipo de imagen se detecta por su contenido real (PNG, JPG, WebP, GIF, BMP, TIFF); SVG y HTML se rechazan.
- Todo archivo servido por la API sale con `Content-Security-Policy: sandbox` y `nosniff`.
- El nombre de archivo se limpia antes de ponerlo en las cabeceras.
- Prueba: `test_svg_o_html_disfrazados_de_imagen_no_entran`.

### 3.2 Dependencias con 52 vulnerabilidades conocidas — CORREGIDO

pyjwt 2.9 (22), Starlette 0.38 (14), python-multipart 0.0.9 (14) y pytest (2). Se actualizó a FastAPI 0.161.1, Starlette 1.9.0, PyJWT 2.15.1, python-multipart 0.0.32 y pytest 9.0.3. La suite completa pasa con las versiones nuevas y `pip-audit` no reporta nada.

### 3.3 La web no tenía política de seguridad de contenido (CSP) — CORREGIDO

Se agregó en Caddy una CSP estricta: solo se ejecuta código del propio sistema. Para lograrlo:

- se quitaron los scripts en línea (la impresión se lanza desde la app y el tema va en `tema.js`);
- se desactivó la carga de estilos con `onload` en línea.

Verificado sin violaciones en 14 pantallas.

### 3.4 Respuestas inconsistentes con datos de otra clínica — CORREGIDO (no había fuga)

Tres listados (créditos, enlaces del portal y sugerencias de IA de un paciente ajeno) respondían con una lista vacía en lugar de 404. No exponían datos, pero ahora responden 404 como el resto de la API.

### 3.5 Lista de pacientes sin paginar — CORREGIDO

Con 5.000 pacientes, `/patients` devolvía los 5.000 de una vez (838 KB). Ahora devuelve 300 por página, con el total en `X-Total-Count`. La web y la app avisan cuando hay más y la búsqueda encuentra a cualquiera.

### 3.6 Sin forma de recuperar la clave del único administrador — CORREGIDO

Un odontólogo que trabaja solo y olvida su clave no tenía salida (no hay correo y es el único administrador). Nuevo comando: `odonto restablecer-clave correo@consultorio.com`.

### 3.7 El chequeo de salud no revisaba la base de datos — CORREGIDO

`/api/v1/health` respondía «ok» aunque PostgreSQL estuviera caído. Ahora consulta la base y responde 503 si no hay conexión, para que Docker y el monitoreo lo detecten.

## 4. Rendimiento medido

Instalación de producción local, 2 procesos del backend. Volumen: 5.000 pacientes, 30.000 citas, 10.000 cargos y 10.000 cobros.

| Operación | 1 petición | 10 simultáneas (p95) |
|---|---|---|
| Buscar paciente | ~50 ms | 118 ms |
| Agenda de la semana | ~76 ms | 138 ms |
| Cuenta de un paciente | ~41 ms | 55 ms |
| Lista de pacientes (300) | — | NO VERIFICADO tras paginar (antes: 89 ms con 5.000) |
| Panel principal | 172 ms | 944 ms |
| Resumen financiero | 164 ms | 958 ms |
| Reportes | 291 ms | 1,8 s |
| Oportunidades | 420 ms | 2,4 s |
| Cartera (todos los pacientes) | 669 ms · 4,6 MB | 3,3 s |

**Conclusión:** sobrado para un consultorio y adecuado para una clínica mediana. La cartera descarga todo de una vez (4,6 MB con este volumen); conviene paginarla o resumirla antes de clínicas grandes. Ver pendiente M4.

## 5. Pendiente antes de vender a escala

### Críticos para comercializar en Ecuador

| # | Pendiente | Por qué importa |
|---|---|---|
| C1 | **Facturación electrónica del SRI** | El sistema emite recibos, estados de cuenta y presupuestos con la leyenda «no es comprobante de venta». La clínica necesita otro sistema para facturar. Es lo primero que preguntará un cliente. |
| C2 | **Revisión legal de los textos** | Aviso de privacidad, acuerdo de confidencialidad, Términos de uso y contrato de encargo (LOPDP) son una base razonable, pero los debe revisar un abogado ecuatoriano antes de firmar con clientes. También falta el contrato comercial del servicio (precio, nivel de servicio, soporte, terminación). |
| C3 | **Respaldos fuera del servidor automáticos** | Hoy el respaldo diario queda en el mismo servidor; copiarlo fuera (rclone o snapshots) está documentado pero hay que configurarlo a mano en cada instalación. Si se pierde el VPS sin esa copia, se pierde todo. |
| C4 | **Instalación real en un VPS con dominio** | El instalador `scripts/instalar-vps.sh` y el certificado de Let's Encrypt **NO VERIFICADOS** en un VPS real: aquí se probó con `localhost` y certificado interno. Hacer una instalación completa de ensayo antes del primer cliente. |

### Importantes

| # | Pendiente |
|---|---|
| M1 | **Monitoreo y alertas:** no hay captura de errores (tipo Sentry) ni alertas. Mínimo: UptimeRobot sobre `/api/v1/health` (documentado) y revisar `odonto logs`. |
| M2 | **Diagnósticos sin código CIE-10:** el MSP trabaja con CIE-10 (capítulo K00–K14 para odontología). Hoy el diagnóstico es texto libre. |
| M3 | **Pruebas automáticas de la web:** casi no existen (1 archivo de prueba). Las pantallas se verificaron con recorridos automáticos durante esta auditoría, pero conviene una suite E2E (Playwright) que corra en cada versión. |
| M4 | **Cartera y oportunidades en clínicas grandes:** con miles de pacientes tardan 0,4 a 0,7 s solos y hasta 3 s con 10 usuarios a la vez. Paginar o resumir. |
| M5 | **App para iPhone: NO VERIFICADA** (no se compiló ni probó en iOS). La app Android compila, pero **no se probó en un teléfono físico**: se probó en la versión de escritorio y en la web. |
| M6 | **Firma de publicación en Play Store:** configurable (`key.properties`, ver `docs/PUBLICAR_APP.md`) pero aún sin llave real. |
| M7 | **Límite de peticiones:** solo están limitados el ingreso (10 por minuto), la renovación de sesión y el portal. El límite general de 200 por minuto que figura en el código no está activo (falta el middleware). No bloquea a nadie, pero tampoco frena abusos sobre otras rutas. |

### Menores

| # | Pendiente |
|---|---|
| m1 | Sin verificación en dos pasos (2FA) para administradores. |
| m2 | Archivos clínicos y base de datos sin cifrado en reposo (depende del disco del VPS). |
| m3 | La app móvil requiere conexión: no funciona sin internet. |
| m4 | Accesibilidad (lectores de pantalla, contraste, teclado): **NO VERIFICADA**. |
| m5 | Un solo servidor sin réplica: si el VPS cae, el servicio cae hasta restaurarlo (los snapshots del proveedor lo mitigan). |

## 6. Lo que sí está listo (verificado en código y pruebas)

- **Multiclínica real:** cada clínica ve solo lo suyo (sección 2, fila 6).
- **Permisos por rol** en todas las rutas privadas, con prueba de acceso denegado.
- **Registros clínicos que no se borran:** evoluciones, diagnósticos, recetas, consentimientos, cobros, cargos, presupuestos y planes se anulan con motivo y quedan en la auditoría.
- **LOPDP:**
  - aviso de privacidad versionado y constancia de entrega;
  - autorización de comunicaciones revocable;
  - registro de quién abrió cada ficha;
  - exportación de datos del paciente;
  - solicitudes de los titulares con plazo de 15 días;
  - delegado de protección de datos;
  - términos aceptados con fecha y versión.
- **Seguridad de sesión:**
  - contraseñas con política y Argon2;
  - cambio obligatorio de la clave temporal;
  - cookie de refresco HttpOnly y Secure en producción;
  - cierre por inactividad configurable;
  - el servidor se niega a arrancar en producción con configuración insegura.
- **Operación:**
  - instalación de un comando;
  - `odonto` para estado, registros, actualizar (con respaldo previo), respaldar, restaurar, alta de clientes y recuperar claves;
  - respaldo diario verificado;
  - rotación de registros;
  - migraciones automáticas.
- **CRUD completo** en todos los módulos (auditoría del 16 de octubre).

## 7. Lista de verificación para el primer cliente

- [ ] Instalación de ensayo en un VPS real con dominio y HTTPS válido (C4).
- [ ] Respaldos copiándose fuera del servidor y una restauración de prueba en otro servidor (C3).
- [ ] Textos legales revisados por un abogado y contrato de servicio firmado (C2).
- [ ] Acordar con el cliente cómo facturará mientras no exista la integración con el SRI (C1).
- [ ] UptimeRobot vigilando `/api/v1/health` (M1).
- [ ] App Android instalada y probada en el teléfono del cliente (M5).
- [ ] `PROVIDER_NAME`, `PROVIDER_TAX_ID` y `PROVIDER_EMAIL` con los datos de su empresa.
- [ ] Capacitación: alta de usuarios, permisos, cobros, respaldos.

## Cómo repetir las verificaciones

```bash
cd backend && .venv/bin/pytest -q                          # 224 pruebas, incluye aislamiento entre clínicas
.venv/bin/pytest -q -s tests/test_aislamiento_clinicas.py  # muestra cuántas rutas se probaron
pip install pip-audit && pip-audit -r requirements.txt     # vulnerabilidades conocidas
cd ../mobile && flutter analyze && flutter test
cd ../frontend && node_modules/.bin/ng build
```
