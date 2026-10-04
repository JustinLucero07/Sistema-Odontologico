# Instalación en producción

Guía para instalar el sistema para un consultorio o una clínica, en un servidor propio o en la nube, con HTTPS y respaldos automáticos. Toma unos 20 minutos.

## Qué se necesita

- Un servidor Linux con Docker y Docker Compose. Basta un VPS de 2 GB de RAM y 40 GB de disco para una clínica o para varios consultorios pequeños.
- Un dominio o subdominio (por ejemplo, `sonrisa.sudominio.com`) apuntando a la IP del servidor.
- Los puertos 80 y 443 abiertos.

## 1. Configurar

```bash
git clone <repositorio> /opt/odonto
cd /opt/odonto/infra
cp .env.prod.example .env.prod
nano .env.prod
```

Complete:

| Variable | Qué poner |
|---|---|
| `DOMINIO` | El dominio, sin `https://` |
| `CORREO_TLS` | Un correo para avisos del certificado |
| `POSTGRES_PASSWORD` | Una clave aleatoria |
| `JWT_SECRET_KEY` | Otra clave aleatoria, distinta |

Para generar cada clave:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

## 2. Arrancar

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
```

Al arrancar, el sistema hace solo lo siguiente:

- Obtiene el certificado HTTPS para el dominio y lo renueva cuando toca.
- Aplica las migraciones de la base de datos y pone al día los permisos.
- Se niega a arrancar si la configuración no es segura (claves por defecto, cookies sin HTTPS, etc.).
- Programa un respaldo diario a las 02:00 en `infra/respaldos/`.
- Envía los recordatorios de citas cada 15 minutos.

Compruebe que responde en `https://SU-DOMINIO/api/v1/health`, que debe devolver `{"status":"ok"}`.

## 3. Crear el consultorio o la clínica del cliente

**Odontólogo independiente** (él mismo administra y atiende):

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod exec backend \
  python nueva_clinica.py \
    --nombre "Consultorio Dra. Lucía Paz" \
    --admin-email lucia.paz@correo.ec \
    --admin-nombre "Lucía" --admin-apellido "Paz" \
    --odontologo --registro "MSP-12345"
```

Con `--odontologo`, la cuenta queda también como profesional: puede agendar citas y firmar recetas con su registro desde el primer ingreso.

**Clínica con equipo:**

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod exec backend \
  python nueva_clinica.py \
    --nombre "Clínica Dental Sonrisa" \
    --admin-email dra.perez@sonrisa.ec \
    --admin-nombre "Ana" --admin-apellido "Pérez" \
    --ruc 1790000000001 --telefono "+593 99 999 9999" \
    --direccion "Av. Amazonas N24-03, Quito"
```

El comando imprime una **contraseña temporal** una sola vez. Entréguela por un canal seguro; el sistema obliga a cambiarla en el primer ingreso. La clínica se crea sin datos de demostración, con roles, permisos y un catálogo inicial de 20 tratamientos con precios orientativos que la clínica ajusta.

> No ejecute `seed.py` en producción: crea una clínica de demostración con contraseñas conocidas.

## 4. Primeros pasos de la clínica

1. Entrar con la contraseña temporal y cambiarla.
2. Aceptar el acuerdo de confidencialidad.
3. Completar *Configuración › Datos de la clínica* (razón social, RUC, dirección y correo). El aviso de privacidad toma estos datos.
4. Ajustar precios en *Configuración › Tratamientos*.
5. Registrar los profesionales y crear los usuarios del personal con su rol.
6. En la app móvil, pulsar **«Configurar servidor de la clínica»** en el login y escribir el dominio.

## 5. Actualizar a una versión nueva

```bash
cd /opt/odonto && git pull
cd infra && docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
```

Las migraciones y los permisos nuevos se aplican solos.

## 6. Respaldos

- Se guardan cada día en `infra/respaldos/`: `odonto-FECHA.dump` (la base de datos) y `archivos-FECHA.tar.gz` (radiografías y documentos).
- Cada volcado se verifica: si no contiene la tabla de pacientes, se renombra a `.SOSPECHOSO`.
- La retención es de 30 días (`RETENCION_DIAS`).
- **Copie los respaldos fuera del servidor** (otro disco, otra nube). Un respaldo en la misma máquina no protege de perder esa máquina.

Para restaurar un volcado:

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod exec -T postgres \
  pg_restore -U odonto -d odonto --clean --if-exists < respaldos/odonto-FECHA.dump
```

## 7. WhatsApp (opcional)

Sin configurar, los recordatorios quedan registrados como «simulado» y nada se envía. Para enviarlos de verdad se necesita una cuenta de WhatsApp Business Cloud API (Meta). Ponga `WHATSAPP_TOKEN` y `WHATSAPP_PHONE_NUMBER_ID` en `.env.prod` y reinicie.

Los botones de WhatsApp de *Oportunidades* y de la ficha no necesitan esta cuenta: abren WhatsApp en el equipo con el mensaje ya escrito.

## 8. Varios consultorios o clínicas en un servidor

Cada consultorio o clínica es un inquilino aislado (`clinic_id`), así que pueden convivir varios en la misma instalación, cada uno viendo solo sus datos. Basta repetir `nueva_clinica.py`. Es la forma más económica de atender a odontólogos independientes. Si prefiere aislamiento total por cliente, haga una instalación por clínica, con su propio dominio.
