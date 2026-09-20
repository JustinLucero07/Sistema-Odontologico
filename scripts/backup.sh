#!/usr/bin/env bash
#
# Respaldo de la base de datos y de los archivos clínicos.
#
# Un respaldo que nunca se ha restaurado no es un respaldo: es un archivo. Por
# eso este script NO termina al escribir el volcado — lo restaura en una base
# desechable y comprueba que las tablas están, antes de declararlo bueno. Si la
# verificación falla, el archivo se marca como .SOSPECHOSO y el script sale con
# error, de modo que un cron lo reporte en vez de acumular basura en silencio.
#
#   ./scripts/backup.sh                    # respaldo + verificación
#   ./scripts/backup.sh --no-verify        # solo volcado (más rápido)
#   RETENTION_DAYS=30 ./scripts/backup.sh  # cambiar la retención
#
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="${BACKUP_DIR:-$ROOT/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
STORAGE_DIR="${STORAGE_DIR:-$ROOT/backend/storage}"
VERIFY=1
[[ "${1:-}" == "--no-verify" ]] && VERIFY=0

# --- Conexión -------------------------------------------------------------
# Se lee del mismo .env que usa la aplicación, para que un respaldo no pueda
# apuntar a una base distinta de la que se está sirviendo.
ENV_FILE="$ROOT/backend/.env"
[[ -f "$ENV_FILE" ]] || { echo "No se encontró $ENV_FILE" >&2; exit 1; }
DB_URL="$(grep -E '^DATABASE_URL=' "$ENV_FILE" | head -1 | cut -d= -f2-)"
[[ -n "$DB_URL" ]] || { echo "DATABASE_URL no está definida en $ENV_FILE" >&2; exit 1; }

# postgresql+asyncpg://user:pass@host:port/db  ->  partes sueltas
CLEAN="${DB_URL#*://}"
CREDS="${CLEAN%%@*}"; HOSTPART="${CLEAN#*@}"
DB_USER="${CREDS%%:*}"; DB_PASS="${CREDS#*:}"
HOSTPORT="${HOSTPART%%/*}"; DB_NAME="${HOSTPART#*/}"; DB_NAME="${DB_NAME%%\?*}"
DB_HOST="${HOSTPORT%%:*}"; DB_PORT="${HOSTPORT#*:}"; [[ "$DB_PORT" == "$DB_HOST" ]] && DB_PORT=5432
export PGPASSWORD="$DB_PASS"

STAMP="$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"
DUMP="$BACKUP_DIR/odonto-$STAMP.dump"

echo "==> Volcando $DB_NAME desde $DB_HOST:$DB_PORT"
# Formato custom: comprimido, y restaurable tabla por tabla con pg_restore.
pg_dump --host="$DB_HOST" --port="$DB_PORT" --username="$DB_USER" \
        --dbname="$DB_NAME" --format=custom --compress=6 --file="$DUMP"
echo "    $(du -h "$DUMP" | cut -f1)  $DUMP"

# --- Archivos clínicos ----------------------------------------------------
# Las radiografías no están en la base. Un respaldo sin ellas restaura una
# historia clínica que apunta a imágenes que ya no existen.
if [[ -d "$STORAGE_DIR" ]]; then
  FILES="$BACKUP_DIR/archivos-$STAMP.tar.gz"
  tar -czf "$FILES" -C "$(dirname "$STORAGE_DIR")" "$(basename "$STORAGE_DIR")"
  echo "    $(du -h "$FILES" | cut -f1)  $FILES"
else
  echo "    (sin carpeta de archivos en $STORAGE_DIR)"
fi

# --- Verificación ---------------------------------------------------------
if [[ "$VERIFY" == "1" ]]; then
  CHECK_DB="verify_${STAMP//-/_}"
  echo "==> Verificando: restaurando en la base desechable $CHECK_DB"
  cleanup() {
    psql --host="$DB_HOST" --port="$DB_PORT" --username="$DB_USER" --dbname=postgres \
         -q -c "DROP DATABASE IF EXISTS $CHECK_DB" >/dev/null 2>&1 || true
  }
  trap cleanup EXIT

  psql --host="$DB_HOST" --port="$DB_PORT" --username="$DB_USER" --dbname=postgres \
       -q -c "CREATE DATABASE $CHECK_DB"
  # pg_restore avisa de extensiones que ya existen; eso no invalida el volcado,
  # así que se ignora su código de salida y se comprueba el RESULTADO.
  pg_restore --host="$DB_HOST" --port="$DB_PORT" --username="$DB_USER" \
             --dbname="$CHECK_DB" --no-owner --no-privileges "$DUMP" >/dev/null 2>&1 || true

  TABLES=$(psql --host="$DB_HOST" --port="$DB_PORT" --username="$DB_USER" --dbname="$CHECK_DB" \
           -tA -c "SELECT count(*) FROM information_schema.tables WHERE table_schema='public'")
  PATIENTS=$(psql --host="$DB_HOST" --port="$DB_PORT" --username="$DB_USER" --dbname="$CHECK_DB" \
             -tA -c "SELECT count(*) FROM patients" 2>/dev/null || echo "ERROR")
  SOURCE_PATIENTS=$(psql --host="$DB_HOST" --port="$DB_PORT" --username="$DB_USER" --dbname="$DB_NAME" \
                    -tA -c "SELECT count(*) FROM patients")

  echo "    tablas restauradas: $TABLES"
  echo "    pacientes: $PATIENTS (origen: $SOURCE_PATIENTS)"

  if [[ "$TABLES" -lt 30 || "$PATIENTS" == "ERROR" || "$PATIENTS" != "$SOURCE_PATIENTS" ]]; then
    mv "$DUMP" "$DUMP.SOSPECHOSO"
    echo "!!! La verificación FALLÓ. El archivo se renombró a $DUMP.SOSPECHOSO" >&2
    exit 1
  fi
  echo "    verificación correcta"
fi

# --- Retención ------------------------------------------------------------
echo "==> Eliminando respaldos con más de $RETENTION_DAYS días"
find "$BACKUP_DIR" -maxdepth 1 -name 'odonto-*.dump' -mtime "+$RETENTION_DAYS" -print -delete || true
find "$BACKUP_DIR" -maxdepth 1 -name 'archivos-*.tar.gz' -mtime "+$RETENTION_DAYS" -print -delete || true

echo "==> Listo. Respaldos en $BACKUP_DIR:"
ls -1sh "$BACKUP_DIR" | tail -6
