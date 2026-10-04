# Sistema Odontológico

Software de gestión dental para **odontólogos independientes, consultorios pequeños y clínicas**: **web + app móvil (Android y Linux)**, con diseño Liquid Glass en modo claro y oscuro.

## Qué incluye

| Área | Funciones |
|---|---|
| Clínica | Panel del día, agenda semanal sin choques de horario, huecos libres, recordatorios automáticos |
| Pacientes | Ficha, historia clínica versionada, odontograma digital, periodontograma, radiografías y fotos, documentos |
| Clínico | Diagnósticos, planes de tratamiento con avance, presupuestos, evoluciones, recetas, consentimientos firmados |
| Finanzas | Cuenta del paciente, caja diaria con arqueo, ingresos y egresos, créditos en cuotas, reportes |
| Gestión | Inventario con alertas, laboratorio con seguimiento de órdenes, profesionales, usuarios, roles y permisos |
| Crecimiento | **Oportunidades**: a quién escribir hoy por WhatsApp, con el mensaje ya escrito |
| Legal | Herramientas para cumplir la LOPDP de Ecuador: aviso de privacidad, autorizaciones, registro de accesos, exportación de datos y confidencialidad del personal |

## Documentación

| Documento | Para qué |
|---|---|
| [docs/INSTALACION_PRODUCCION.md](docs/INSTALACION_PRODUCCION.md) | Instalar para un cliente: HTTPS, respaldos, alta de clínica |
| [docs/PUBLICAR_APP.md](docs/PUBLICAR_APP.md) | Firmar y publicar la app en Google Play |
| [docs/LANZAMIENTO.md](docs/LANZAMIENTO.md) | Lista de lanzamiento: qué está listo y qué falta |
| [docs/VENTAS.md](docs/VENTAS.md) | Guía de venta, demostración y precios |
| [docs/legal/](docs/legal/) | Plantillas de términos de servicio y de contrato de encargo de datos |
| [LEGAL.md](LEGAL.md) | Qué obligaciones legales cubre el sistema y cuáles quedan a cargo de la clínica |
| [OPERACIONES.md](OPERACIONES.md) | Operación diaria, respaldos manuales y variables de entorno |

## Desarrollo

Requisitos: Docker, Python 3.12, Node 20 y Flutter 3.

```bash
# Base de datos de desarrollo
cd infra && docker compose up -d postgres redis

# Backend
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head && python seed.py   # seed.py = datos de DEMOSTRACIÓN
uvicorn app.main:app --reload

# Web (http://localhost:4200)
cd frontend && npm install && npm start

# App
cd mobile && flutter run -d linux        # o un emulador Android
```

Credenciales de demostración (solo `seed.py`, nunca en producción): `admin@clinicademo.com` / `Admin123!`

Pruebas: `cd backend && pytest` y `cd mobile && flutter test`.
