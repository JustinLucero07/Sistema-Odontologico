# Instalación en un VPS (paso a paso)

Esta guía deja el sistema funcionando en internet, con su dominio, HTTPS, respaldos diarios y la app del celular conectada. Con el instalador automático toma unos **20–30 minutos**, y no hace falta saber de servidores.

**Cómo funciona:** todo corre en Docker dentro de un VPS (un servidor virtual alquilado). Un mismo servidor puede atender a **muchos clientes**: odontólogos independientes, consultorios y clínicas. Cada uno ve solo sus datos.

```
Internet ──► Caddy (HTTPS automático) ──► Web (Angular)
                                       └─► API (FastAPI) ──► PostgreSQL
                                                          └─► Redis
           + recordatorios cada 15 min + respaldo diario
```

---

## 0. Qué necesita

| Qué | Recomendado | Notas |
|---|---|---|
| VPS | **2 vCPU, 4 GB RAM, 40 GB SSD**, Ubuntu 24.04 | Con 2 GB también funciona (el instalador agrega memoria swap). Para más de 30 clientes, suba a 8 GB. |
| Dominio | Ej. `app.tumarca.com` | Un subdominio de un dominio que ya tenga sirve. |
| Correo | Cualquiera | Para avisos del certificado HTTPS. |

**Proveedores de VPS que funcionan bien** (los precios cambian; revise el actual):

- **Hetzner Cloud** (CX22 o similar): el mejor precio por rendimiento, desde unos 5 USD al mes.
- **Contabo**: muy barato y con más disco; el soporte es más lento.
- **DigitalOcean / Vultr / Linode**: fáciles de usar, desde unos 12 USD al mes con 2 GB.

Elija la región más cercana a sus clientes. Para Ecuador suelen ir bien Estados Unidos este (Virginia o Nueva York) y Miami.

---

## 1. Crear el servidor

1. En el panel del proveedor, cree un servidor con **Ubuntu 24.04**.
2. Recomendado: agregue su **llave SSH** en lugar de usar contraseña. En su computadora:
   ```bash
   ssh-keygen -t ed25519      # Enter a todo, si aún no tiene una
   cat ~/.ssh/id_ed25519.pub  # copie esto en el panel del proveedor
   ```
3. Anote la **IP pública** del servidor, por ejemplo `203.0.113.10`.

## 2. Apuntar el dominio al servidor

En el panel donde compró el dominio (GoDaddy, Namecheap, Cloudflare, etc.), cree un registro DNS:

| Tipo | Nombre | Valor | TTL |
|---|---|---|---|
| A | `app` (o `@` si usa el dominio principal) | La IP del servidor | Automático |

> Si usa **Cloudflare**, deje la nube en **gris** («Solo DNS») durante la instalación, para que el certificado HTTPS se emita sin problemas. Después puede activarla.

Compruebe desde su computadora que ya apunta (puede tardar unos minutos):

```bash
ping app.tumarca.com
```

## 3. Entrar al servidor

```bash
ssh root@203.0.113.10
```

## 4. Subir el sistema al servidor

**Opción A: desde GitHub (recomendada, facilita actualizar después)**

Como el repositorio es privado, el servidor necesita permiso de solo lectura:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/github -N ""
cat ~/.ssh/github.pub
```

Copie esa llave en GitHub, en *Repositorio › Settings › Deploy keys › Add deploy key* (sin marcar «Allow write access»). Luego:

```bash
cat >> ~/.ssh/config <<'EOF'
Host github.com
  IdentityFile ~/.ssh/github
EOF
git clone git@github.com:JustinLucero07/Sistema-Odontologico.git /opt/odonto
```

**Opción B: copiar desde su computadora**, sin GitHub:

```bash
# En SU computadora, dentro de la carpeta del sistema:
rsync -av --exclude node_modules --exclude .venv --exclude build --exclude .dart_tool \
  ./ root@203.0.113.10:/opt/odonto/
```

## 5. Ejecutar el instalador

```bash
cd /opt/odonto
sudo bash scripts/instalar-vps.sh
```

El instalador le pregunta tres cosas:

1. El **dominio** (por ejemplo `app.tumarca.com`).
2. Un **correo** para el certificado HTTPS.
3. El **nombre de su empresa**, que sale en los Términos de uso que aceptan sus clientes.

Y hace todo lo demás, sin intervención:

- [x] Actualiza Ubuntu y activa las **actualizaciones de seguridad automáticas**.
- [x] Instala **fail2ban** (bloquea los intentos de adivinar la contraseña de SSH).
- [x] Agrega **memoria swap** si el servidor tiene poca RAM.
- [x] Instala **Docker**.
- [x] Configura el **firewall**: solo SSH, 80 y 443. La base de datos nunca queda expuesta.
- [x] Crea `infra/.env.prod` con **claves aleatorias seguras**.
- [x] Comprueba que el dominio apunte al servidor.
- [x] Compila y arranca todo, con **HTTPS automático** (Let's Encrypt, que se renueva solo).
- [x] Instala el comando **`odonto`** para administrar el servidor.

Al terminar, abra `https://app.tumarca.com`: debe aparecer la pantalla de ingreso.

> **Guarde una copia de `infra/.env.prod`** en un lugar seguro, como un gestor de contraseñas. Contiene la clave de la base de datos, y sin ella los respaldos no se pueden restaurar en otro servidor.

## 6. Crear su primer cliente

**Odontólogo que trabaja solo** (es administrador y a la vez el profesional que atiende):

```bash
odonto nueva-clinica --nombre "Consultorio Dra. Ana Paz" \
  --admin-email ana@correo.com --admin-nombre Ana --admin-apellido Paz \
  --odontologo --registro "MSP-12345"
```

**Consultorio pequeño o clínica con equipo:**

```bash
odonto nueva-clinica --nombre "Clínica Dental Sonrisa" \
  --admin-email admin@sonrisa.ec --admin-nombre Ana --admin-apellido Pérez \
  --ruc 1790000000001 --telefono "0991234567" --direccion "Av. Amazonas N24-03, Quito"
```

El comando muestra una **contraseña temporal una sola vez**. Entréguela al cliente por un canal seguro, por ejemplo por WhatsApp en un mensaje aparte del correo.

**Lo que ve el cliente al entrar la primera vez:**

1. Cambia la contraseña temporal por una propia.
2. Acepta el acuerdo de confidencialidad.
3. Sigue el **asistente de bienvenida**: si trabaja solo o es una clínica, sus datos, su logo y sus colores, su horario, qué módulos quiere ver, y la aceptación de los Términos de uso. Se hace una sola vez, en la web o en el celular.
4. Completa *Configuración › Legal y cumplimiento*: representante legal, SRI, permiso de funcionamiento y delegado de datos.
5. Ajusta los precios en *Configuración › Tratamientos* y crea los usuarios de su personal.

**App del celular:** en la pantalla de ingreso, toque **«Configurar servidor del consultorio»** y escriba `app.tumarca.com`. Para no tener que hacerlo en cada celular, puede publicar la app con el servidor fijo (vea `docs/PUBLICAR_APP.md`).

> No ejecute `seed.py` en producción: crea una clínica de demostración con contraseñas conocidas.

## 7. Respaldos

**Automáticos:** cada día a las 02:00 se guardan en `/opt/odonto/infra/respaldos/`:

- `odonto-FECHA.dump`: la base de datos completa.
- `archivos-FECHA.tar.gz`: radiografías, fotos y documentos.

Cada volcado se verifica (si no contiene la tabla de pacientes, se marca como `.SOSPECHOSO`) y se guardan 30 días.

**Respaldos fuera del servidor (muy importante).** Un respaldo en el mismo servidor no sirve si se pierde el servidor. El sistema trae un servicio que cada noche (a las 02:30) **copia los respaldos a la nube, cifrados antes de salir del servidor**: el proveedor de la nube no puede leerlos.

Se configura una sola vez:

```bash
odonto nube-configurar
```

El asistente le pregunta dónde guardarlos:

| Opción | Costo aproximado | Comentario |
|---|---|---|
| **Backblaze B2** (recomendado) | 10 GB gratis, luego ~6 USD por TB al mes | El más usado para respaldos |
| **Cloudflare R2** | 10 GB gratis | No cobra por descargar |
| **Otro** | Según el servicio | Google Drive, Hetzner Storage Box, Amazon S3, OneDrive… con el asistente de rclone |

**Ejemplo con Backblaze B2:**

1. Cree una cuenta en backblaze.com.
2. En *B2 Cloud Storage › Buckets › Create a Bucket*, cree uno **privado**, por ejemplo `odonto-respaldos-miempresa`.
3. En *Application Keys › Add a New Application Key*, cree una con acceso de lectura y escritura **solo a ese bucket**.
4. Ejecute `odonto nube-configurar`, elija `1` y pegue el *keyID*, la *applicationKey* y el nombre del bucket.
5. El asistente muestra **una contraseña y una sal de cifrado**. **Guárdelas fuera del servidor** (gestor de contraseñas o papel en un lugar seguro). Sin ellas, los respaldos de la nube no se pueden abrir.
6. Sube los respaldos actuales para comprobar que todo funciona.

**Para revisarlo:**

```bash
odonto estado        # muestra «✔ Copia en la nube: fecha (N respaldos)» o el error
odonto nube-listar   # lo que hay en la nube
odonto nube-subir    # subir ahora (por ejemplo, antes de un cambio grande)
```

Los respaldos se guardan 90 días en la nube (`RETENCION_EXTERNA_DIAS` en `infra/.env.prod`).

Además, active en el panel del proveedor los **snapshots automáticos del VPS** (suelen costar alrededor del 20 % del servidor): permiten volver a levantar el servidor entero en minutos.

#### Copia también en su computadora

Además de la nube, puede bajar los respaldos a su propia computadora (Linux o Mac). Se ejecuta **en su computadora**, no en el servidor, y usa el mismo acceso SSH con el que entra al VPS:

```bash
# Bajar ahora (solo trae lo nuevo y verifica cada respaldo):
scripts/bajar-respaldos.sh root@IP-DEL-SERVIDOR

# Que baje solo todos los días a las 09:00 y al encender la computadora:
scripts/bajar-respaldos.sh root@IP-DEL-SERVIDOR --programar
```

- Quedan en `~/Respaldos-Odonto/IP-DEL-SERVIDOR/`; se guardan 60 días (`DIAS_LOCALES=90 scripts/bajar-respaldos.sh …` para cambiarlo).
- Con varios clientes, prográmelo una vez por servidor: cada uno va a su carpeta.
- Si su SSH usa otro puerto o llave: `SSH_OPCIONES="-p 2222 -i ~/.ssh/vps" scripts/bajar-respaldos.sh …`
- Sin el script, una sola vez: `scp -r root@IP-DEL-SERVIDOR:/opt/odonto/infra/respaldos ~/Respaldos-Odonto/`
- Estos archivos **no van cifrados**: contienen historias clínicas. Use una computadora con el disco cifrado y con contraseña.

Para abrir un respaldo en su computadora y revisarlo (necesita PostgreSQL o Docker):

```bash
createdb copia_clinica
pg_restore --no-owner -d copia_clinica ~/Respaldos-Odonto/IP-DEL-SERVIDOR/odonto-FECHA.dump
```

Y para volver a subirlo a un servidor y restaurarlo: copie el archivo a `/opt/odonto/infra/respaldos/` en el servidor y ejecute `odonto restaurar FECHA`.

#### Si se pierde el servidor

1. Cree un VPS nuevo e instale el sistema (pasos 1 a 5 de esta guía).
2. Ejecute `odonto nube-configurar`, elija el mismo proveedor y el mismo bucket, y responda **«s»** a *¿Es un servidor NUEVO…?*. Ingrese la contraseña y la sal que guardó.
3. `odonto nube-listar` muestra los respaldos disponibles. Elija el más reciente:
   ```bash
   odonto nube-recuperar 20261023-020000
   odonto restaurar 20261023-020000
   ```
4. Restaure también su copia de `infra/.env.prod` (o cree una nueva y cambie las contraseñas de los usuarios).

**Comandos útiles:**

```bash
odonto respaldar                 # respaldo inmediato (local) (por ejemplo, antes de un cambio grande)
odonto respaldos                 # ver los que hay
odonto restaurar 20261011-020000 # volver a ese momento (pide confirmación y respalda antes lo actual)
```

## 8. Uso diario del servidor

```bash
odonto estado        # qué está funcionando, si responde y cuánto disco queda
odonto logs backend  # ver errores en vivo (Ctrl+C para salir)
odonto actualizar    # instalar una versión nueva (hace un respaldo antes)
odonto reiniciar     # reiniciar todo
odonto db            # consola de la base de datos (solo si sabe lo que hace)
```

**Actualizar a una versión nueva:** suba los cambios a GitHub desde su computadora y ejecute en el servidor `odonto actualizar`. Las migraciones de la base de datos se aplican solas.

**Saber si se cae:** cree una cuenta gratis en [UptimeRobot](https://uptimerobot.com) que vigile `https://app.tumarca.com/api/v1/health` cada 5 minutos y le avise por correo o Telegram.

## 9. Opcionales

**WhatsApp automático:** sin configurarlo, los recordatorios quedan registrados como «simulado» y los botones de WhatsApp abren la app con el mensaje ya escrito, que es lo que la mayoría usa. Para envío automático necesita una cuenta de *WhatsApp Business Cloud API* (Meta). Ponga `WHATSAPP_TOKEN` y `WHATSAPP_PHONE_NUMBER_ID` en `infra/.env.prod` y ejecute `odonto reiniciar`.

**Datos de su empresa** en los Términos de uso: edite `PROVIDER_NAME`, `PROVIDER_TAX_ID` y `PROVIDER_EMAIL` en `infra/.env.prod` y reinicie.

**Más rendimiento:** con 4 GB o más de RAM, ponga `WEB_WORKERS=4` en `infra/.env.prod`.

**Un servidor por cliente:** si una clínica grande pide aislamiento total, repita esta guía en otro VPS con su propio dominio.

## 10. Si algo falla

| Síntoma | Causa probable | Qué hacer |
|---|---|---|
| El navegador dice «conexión no segura» o no carga | El dominio aún no apunta al servidor, o el puerto 80/443 está cerrado en el panel del proveedor | `ping` al dominio debe dar la IP del servidor. Revise el firewall del panel del proveedor. Luego `odonto logs caddy` |
| `odonto estado` muestra el backend reiniciándose | Error al arrancar | `odonto logs backend`: el error aparece al final |
| La compilación se corta o «Killed» | Poca memoria | El instalador agrega swap. Si persiste, suba a 4 GB de RAM |
| La app del celular no conecta | Dirección del servidor mal escrita | Escriba solo `app.tumarca.com`, sin `https://` ni barras |
| Se llenó el disco | Respaldos o registros acumulados | `odonto estado` muestra el disco. Baje `RETENCION_DIAS` o amplíe el disco |
| Olvidé la contraseña del administrador de un cliente | — | Otro administrador de esa clínica puede restablecerla desde *Usuarios*. Si no hay otro, cree un administrador nuevo con `odonto db` o escríbanos |

## 11. Lista de seguridad antes de vender

- [ ] HTTPS funciona (candado en el navegador).
- [ ] `infra/.env.prod` guardado fuera del servidor.
- [ ] Respaldos copiándose fuera del servidor (rclone o snapshots).
- [ ] Monitoreo con UptimeRobot.
- [ ] Ingreso por SSH solo con llave (en `/etc/ssh/sshd_config`: `PasswordAuthentication no`, y luego `systemctl restart ssh`).
- [ ] `PROVIDER_NAME` con el nombre de su empresa.
- [ ] Textos legales revisados por un abogado (*Privacidad y legal* en el sistema).

---

### Instalación manual (sin el instalador)

Si prefiere hacerlo a mano, o el servidor no es Ubuntu ni Debian:

```bash
# Docker
curl -fsSL https://get.docker.com | sh
# Configuración
cd /opt/odonto/infra
cp .env.prod.example .env.prod && nano .env.prod   # DOMINIO, CORREO_TLS y dos claves aleatorias:
openssl rand -base64 40                            # una para POSTGRES_PASSWORD y otra para JWT_SECRET_KEY
# Arrancar
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
# Comando de administración
ln -sf /opt/odonto/infra/odonto.sh /usr/local/bin/odonto
```

## Facturación electrónica (SRI)

Cada consulta factura con **su propio RUC y su propia firma electrónica**. El
servidor solo necesita dos cosas, que `instalar-vps.sh` ya deja listas en
instalaciones nuevas:

1. **`CERT_ENCRYPTION_KEY`** en `infra/.env.prod`: la llave con la que se
   cifran las firmas `.p12` guardadas. Si su servidor se instaló antes de esta
   versión, agréguela una vez:

   ```bash
   echo "CERT_ENCRYPTION_KEY=$(openssl rand -base64 32 | tr '+/' '-_')" >> /opt/odonto/infra/.env.prod
   odonto actualizar
   ```

   **No la cambie después**: si cambia, cada consulta debe volver a subir su firma.
   Guárdela junto con las claves de los respaldos.

2. **Correo saliente (opcional)** para que el PDF y el XML lleguen solos al
   paciente: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`
   en el mismo archivo. Sin correo, la factura se envía por WhatsApp o se descarga.

El servicio **facturador** retoma cada minuto lo que quedó pendiente con el SRI
(envíos sin respuesta, autorizaciones en proceso). Se revisa con
`odonto logs facturador`.

Cada consulta, en **Facturación → Configuración**: sube su `.p12` y su clave,
empieza en **Pruebas**, emite facturas de prueba hasta que salgan autorizadas y
recién entonces pasa a **Producción** (después de habilitarla en «SRI en línea»).
