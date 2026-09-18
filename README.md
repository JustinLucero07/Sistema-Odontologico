# Sistema Odontológico — Fases 1 a 4

Arquitectura completa en [este documento](https://claude.ai/code/artifact/8991af38-1531-4963-8933-c9094d25488a).

- **Fase 1**: arquitectura base, autenticación (JWT + refresh rotativo), usuarios, roles y permisos (RBAC configurable), datos de la clínica, sucursales, consultorios y profesionales/especialidades.
- **Fase 2**: pacientes (alta, búsqueda, baja) e historia clínica versionada — cada edición crea una nueva versión, nunca sobrescribe la anterior — con la ficha del paciente como expediente digital.
- **Fase 3**: odontograma digital interactivo (SVG, no imagen estática) con numeración FDI, dentición permanente y temporal, 5 superficies por pieza más condición de diente completo, versionado por snapshots, historial de versiones, y acceso directo desde el menú con buscador de paciente.
- **Fase 4**: diagnósticos, catálogo de tratamientos, planes de tratamiento (con ítems por pieza/diagnóstico, estados y progreso calculado automáticamente) y presupuestos generados desde un plan (subtotal, impuesto, total, y flujo de estados borrador → enviado → visto → aceptado/rechazado que no permite retroceder).

Todo con frontend Angular funcional de extremo a extremo.

## Requisitos

- Docker y Docker Compose
- (Solo para desarrollo sin Docker) Python 3.12 y Node 20

## Levantar todo con Docker Compose (recomendado)

```bash
cd infra
cp .env.example .env   # define JWT_SECRET_KEY con un valor largo y aleatorio
docker compose up -d --build
```

- Frontend: http://localhost (vía Nginx) o http://localhost:4200 (contenedor del frontend directo)
- API: http://localhost/api/v1 (vía Nginx) o http://localhost:8000/api/v1 directo
- Documentación interactiva de la API: http://localhost:8000/docs

La primera vez, aplique las migraciones y cargue los datos de demostración dentro del contenedor del backend:

```bash
docker compose exec backend alembic upgrade head
docker compose exec backend python seed.py
```

## Desarrollo local sin Docker (backend)

```bash
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # ajuste DATABASE_URL/REDIS_URL si no usa Docker para la base de datos
alembic upgrade head
python seed.py
uvicorn app.main:app --reload
```

Tests: `pytest` (requiere una base `odonto_test` en el Postgres apuntado por `tests/conftest.py`).

## Desarrollo local sin Docker (frontend)

```bash
cd frontend
npm install
npm start   # http://localhost:4200, apunta a http://localhost:8000/api/v1 (ver src/environments)
```

## Credenciales de desarrollo (seed.py)

| Rol | Correo | Contraseña |
| --- | --- | --- |
| Administrador (superadmin) | admin@clinicademo.com | Admin123! |
| Odontólogo | odontologo@clinicademo.com | Odonto123! |

**No usar estas credenciales en producción.**

## Estado del proyecto

- ✅ Fase 1: arquitectura, base de datos, autenticación, usuarios, roles, permisos, clínica
- ✅ Fase 2: pacientes, historia clínica versionada, ficha del paciente
- ✅ Fase 3: odontograma digital interactivo versionado (dentición permanente y temporal)
- ✅ Fase 4: diagnósticos, tratamientos, planes de tratamiento con progreso, presupuestos
- ⬜ Fase 5 en adelante: ver el documento de arquitectura, sección "Plan de desarrollo por fases"
