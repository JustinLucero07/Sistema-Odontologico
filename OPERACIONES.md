# Operación e instalación

Guía para poner el sistema en una clínica y mantenerlo. Escrita para quien
instala y opera, no para quien programa.

---

## 1. Antes de arrancar en producción

El servidor **se niega a arrancar** con `ENV=production` si la configuración no
es segura. No es un aviso en el log: es un fallo al inicio, porque cada punto de
esta lista es un error que alguien comete una sola vez, de noche, en casa de un
cliente.

Lo que comprueba:

| Comprobación | Por qué |
|---|---|
| `JWT_SECRET_KEY` no es el valor por defecto y mide ≥32 caracteres | Con la clave por defecto, cualquiera que conozca el proyecto puede firmar tokens válidos |
| `REFRESH_TOKEN_COOKIE_SECURE=true` | Si no, la cookie de sesión viaja en claro |
| `CORS_ORIGINS` no contiene `*` ni orígenes sin TLS | Con credenciales habilitadas, `*` deja que cualquier web actúe en nombre del usuario |
| `DATABASE_URL` no apunta a la base de desarrollo | |
| `STORAGE_LOCAL_PATH` es una ruta absoluta | Una ruta relativa guarda las radiografías junto al código y las pierde al redesplegar |

Generar una clave:

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

En desarrollo las mismas comprobaciones corren, pero solo informan: se ve qué
bloquearía una publicación sin impedir trabajar.

---

## 2. Variables de entorno

Las que no tienen valor por defecto seguro:

```ini
ENV=production
JWT_SECRET_KEY=<64 caracteres aleatorios>
DATABASE_URL=postgresql+asyncpg://usuario:clave@host:5432/odonto
CORS_ORIGINS=["https://clinica.ejemplo.com"]
REFRESH_TOKEN_COOKIE_SECURE=true
STORAGE_LOCAL_PATH=/var/lib/odonto/storage
```

Opcionales. **Sin ellas el sistema funciona entero y es honesto sobre lo que no
hace**: los mensajes quedan como `simulado` y el asistente responde que no está
configurado, en vez de inventar.

```ini
# WhatsApp (API Cloud de Meta). Hacen falta las dos.
WHATSAPP_TOKEN=
WHATSAPP_PHONE_NUMBER_ID=

# Asistente. Sin clave está apagado.
ANTHROPIC_API_KEY=

# Portal del paciente
PORTAL_BASE_URL=https://clinica.ejemplo.com
PORTAL_LINK_DAYS=30
```

---

## 3. Después de cada actualización

```bash
cd backend
alembic upgrade head        # aplica las migraciones pendientes
python sync_permissions.py  # concede a los roles los permisos nuevos
```

**El segundo paso no es opcional.** `seed.py` solo corre una vez, sobre una base
vacía. Cada fase añade códigos de permiso al catálogo, y una clínica instalada
antes se queda sin ellos: las funciones existen, compilan y están probadas, pero
no aparecen en pantalla y **no dan ningún error que lo explique**.

`sync_permissions.py` es aditivo e idempotente. Nunca retira un permiso que un
administrador haya quitado a propósito.

Los usuarios afectados deben volver a iniciar sesión.

---

## 4. Respaldos

```bash
./scripts/backup.sh                    # respaldo + verificación
./scripts/backup.sh --no-verify        # solo volcado, más rápido
RETENTION_DAYS=30 ./scripts/backup.sh  # cambiar la retención (por defecto 14)
```

Un respaldo que nunca se ha restaurado no es un respaldo: es un archivo. Por eso
el script **no termina al escribir el volcado**. Lo restaura en una base
desechable y comprueba que las tablas están y que el número de pacientes
coincide con el origen. Si la verificación falla, renombra el archivo a
`.SOSPECHOSO` y sale con error, para que el cron lo reporte en vez de acumular
basura en silencio.

Respalda **dos cosas**:

- `odonto-<fecha>.dump` — la base de datos
- `archivos-<fecha>.tar.gz` — las radiografías y documentos

Las imágenes no están en la base. Un respaldo sin ellas restaura historias
clínicas que apuntan a archivos que ya no existen.

En cron, todos los días a las 2:30:

```cron
30 2 * * * cd /opt/odonto && ./scripts/backup.sh >> /var/log/odonto-backup.log 2>&1
```

Los respaldos contienen historias clínicas completas. Están en `.gitignore` y
deben guardarse cifrados y fuera del mismo servidor.

### Restaurar

```bash
./scripts/restore.sh backups/odonto-20260920-170615.dump
```

Pide escribir el nombre de la base para confirmar, porque sobrescribe la que
está en uso.

---

## 5. Recordatorios de citas

Los recordatorios se programan solos al crear una cita, pero algo tiene que
enviarlos. El despachador es un endpoint, no un bucle escondido, para que se
pueda disparar desde cron y ver qué pasó:

```cron
*/15 * * * * curl -fsS -X POST https://clinica.ejemplo.com/api/v1/messaging/dispatch \
  -H "Authorization: Bearer $TOKEN_DE_SERVICIO"
```

Es idempotente: ejecutarlo de más nunca manda el mismo recordatorio dos veces.

---

## 6. Rendimiento

Los índices del sistema se añadieron **con una medición detrás**, no por
costumbre. Medido sobre volumen sintético en una transacción deshecha:

| Consulta | Volumen | Antes | Después |
|---|---|---|---|
| Auditoría, 50 más recientes | 200 000 filas | 14,9 ms | 0,047 ms |
| Historial de un artículo | 60 000 filas | 5,6 ms | 0,048 ms |
| Reporte financiero por fechas | 150 000 filas | 11,2 ms | 0,52 ms |

Tres cosas se midieron y **no** se indexaron:

- Un índice parcial sobre cargos vigentes movió 6,85 ms a 6,66 ms: casi todos
  los cargos están vigentes, así que el índice selecciona la tabla entera.
- La agenda ya resuelve en 0,05 ms con 80 000 citas, por el índice de fechas
  que ya existía.
- `role_permissions` y `user_roles` se leen en **cada petición**, pero tienen
  decenas de filas y nunca tendrán más. Un escaneo de 40 filas gana a una
  búsqueda por índice; indexarlas sería un ritual.

Cada índice cuesta velocidad de escritura. Los que se quedan son los que tienen
un número detrás.

> Si se añade un índice, hay que **declararlo en el modelo**, no solo en la
> migración. Un índice que solo existe en la migración es invisible para
> `alembic revision --autogenerate`, que propondrá borrarlo en la siguiente
> migración — y lo hará.

---

## 7. Qué protege el sistema por sí solo

- **Bloqueo por intentos**: 8 fallos consecutivos bloquean la cuenta 15 minutos.
  El límite por IP no cubre un ataque distribuido contra *una* cuenta, que es la
  forma que toma un intento contra el correo de un odontólogo conocido.
- **Mismas respuestas**: un correo inexistente y una contraseña equivocada dan
  la misma respuesta. Distinguirlas revela qué correos son reales.
- **Cabeceras** en cada respuesta: `nosniff`, `DENY` de marcos, `no-referrer`
  (un token de portal viaja en la URL), CSP restrictiva y `no-store` en todo lo
  clínico. HSTS solo sobre HTTPS.
- **Enlaces de portal**: guardados hasheados, caducan, se revocan, y un token
  desconocido, caducado o revocado dan **la misma** respuesta.
