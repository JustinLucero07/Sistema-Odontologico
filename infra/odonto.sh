#!/usr/bin/env bash
# Administración del sistema en el servidor. Tras instalar-vps.sh queda como
# el comando «odonto». Escriba «odonto» sin nada para ver la ayuda.

set -euo pipefail

INFRA="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
RAIZ="$(dirname "$INFRA")"
ENV="$INFRA/.env.prod"
[ -f "$ENV" ] || { echo "Falta $ENV. Ejecute primero scripts/instalar-vps.sh" >&2; exit 1; }
DC=(docker compose -f "$INFRA/docker-compose.prod.yml" --env-file "$ENV")
set -a; . "$ENV"; set +a
SELLO=$(date +%Y%m%d-%H%M%S)

ayuda() {
  cat <<'EOF'
Uso: odonto <comando>

  estado                 Qué está funcionando y si responde
  logs [servicio]        Registros en vivo (backend, caddy, postgres, frontend…)
  actualizar             Descarga la versión nueva (git pull) y la aplica
  reiniciar              Reinicia todos los servicios
  detener                Detiene todo (los datos se conservan)
  iniciar                Arranca todo

  nueva-clinica ...      Crea un cliente nuevo (mismos parámetros que nueva_clinica.py)
  restablecer-clave CORREO  Clave temporal para un usuario que olvidó la suya
  respaldar [etiqueta]   Hace un respaldo ahora mismo
  respaldos              Lista los respaldos guardados
  restaurar ID           Restaura base y archivos de un respaldo
                         (el ID es lo que va entre «odonto-» y «.dump», ej. 20261011-020000)

  db                     Abre la consola de la base de datos
EOF
}

case "${1:-}" in
  estado)
    "${DC[@]}" ps
    echo
    if curl -fs --max-time 8 "https://${DOMINIO}/api/v1/health" >/dev/null 2>&1; then
      echo "✔ https://${DOMINIO} responde"
    else
      echo "✘ https://${DOMINIO} no responde. Revise: odonto logs caddy / odonto logs backend"
    fi
    df -h / | awk 'NR==2 {print "Disco: " $3 " usados de " $2 " (" $5 ")"}'
    ;;
  logs)
    shift; "${DC[@]}" logs -f --tail 200 "$@" ;;
  actualizar)
    echo "Respaldo previo por seguridad…"; "$0" respaldar antes-de-actualizar
    git -C "$RAIZ" pull --ff-only
    "${DC[@]}" up -d --build
    docker image prune -f >/dev/null
    echo "✔ Actualizado. Las migraciones se aplicaron solas al arrancar."
    ;;
  reiniciar) "${DC[@]}" restart ;;
  detener)   "${DC[@]}" stop ;;
  iniciar)   "${DC[@]}" up -d ;;
  nueva-clinica)
    shift; "${DC[@]}" exec backend python nueva_clinica.py "$@" ;;
  restablecer-clave)
    shift; "${DC[@]}" exec backend python restablecer_clave.py "$@" ;;
  respaldar)
    mkdir -p "$INFRA/respaldos"
    ID="${SELLO}${2:+-$2}"
    # Nunca se pisa un respaldo existente.
    while [ -e "$INFRA/respaldos/odonto-$ID.dump" ]; do ID="$ID-b"; done
    "${DC[@]}" exec -T respaldos sh -c "pg_dump -h postgres -U odonto -d odonto -Fc -f /respaldos/odonto-${ID}.dump && tar -czf /respaldos/archivos-${ID}.tar.gz -C /storage ."
    echo "✔ Respaldo ${ID} en $INFRA/respaldos"
    ;;
  respaldos)
    ls -lh "$INFRA/respaldos" 2>/dev/null || echo "Aún no hay respaldos." ;;
  restaurar)
    F="${2:-}"
    [ -n "$F" ] && [ -f "$INFRA/respaldos/odonto-$F.dump" ] || { echo "Indique la fecha de un respaldo existente. Vea: odonto respaldos" >&2; exit 1; }
    read -rp "Esto REEMPLAZA los datos actuales por los del respaldo $F. Escriba RESTAURAR para seguir: " r
    [ "$r" = "RESTAURAR" ] || { echo "Cancelado."; exit 1; }
    echo "Respaldo de lo actual antes de restaurar…"; "$0" respaldar antes-de-restaurar
    "${DC[@]}" stop backend recordatorios
    "${DC[@]}" exec -T postgres pg_restore -U odonto -d odonto --clean --if-exists < "$INFRA/respaldos/odonto-$F.dump"
    if [ -f "$INFRA/respaldos/archivos-$F.tar.gz" ]; then
      "${DC[@]}" run --rm --no-deps -T --entrypoint sh -v "$INFRA/respaldos:/r:ro" backend \
        -c "find /app/storage -mindepth 1 -delete && tar -xzf /r/archivos-$F.tar.gz -C /app/storage"
    fi
    "${DC[@]}" start backend recordatorios
    echo "✔ Restaurado el respaldo $F"
    ;;
  db) "${DC[@]}" exec postgres psql -U odonto -d odonto ;;
  *) ayuda ;;
esac
