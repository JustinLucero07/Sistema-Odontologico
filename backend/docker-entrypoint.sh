#!/bin/sh
# Al arrancar: aplica migraciones y pone al día los permisos, luego sirve.
# Así una actualización es solo «docker compose up -d --build».
set -e
alembic upgrade head
python sync_permissions.py
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 \
  --workers "${WEB_WORKERS:-2}" --proxy-headers --forwarded-allow-ips="*"
