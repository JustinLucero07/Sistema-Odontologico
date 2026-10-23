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

  nube-configurar        Asistente: conectar la copia de respaldos a la nube (cifrada)
  nube-subir             Sube ahora los respaldos a la nube
  nube-listar            Lista los respaldos guardados en la nube
  nube-recuperar ID      Descarga un respaldo de la nube (luego: odonto restaurar ID)

  db                     Abre la consola de la base de datos
EOF
}

RCLONE=(docker run --rm -i -v "$INFRA/rclone:/config/rclone" -v "$INFRA/respaldos:/respaldos" rclone/rclone:1.68.2)

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
    if [ -f "$INFRA/estado/externo.txt" ]; then
      read -r EST FECHA HORA RESTO < "$INFRA/estado/externo.txt"
      case "$EST" in
        OK) echo "✔ Copia en la nube: $FECHA $HORA ($RESTO)" ;;
        SIN_CONFIGURAR) echo "✘ Copia en la nube SIN CONFIGURAR: ejecute «odonto nube-configurar»" ;;
        *) echo "✘ Copia en la nube con ERROR el $FECHA $HORA: $RESTO" ;;
      esac
    else
      echo "✘ Copia en la nube SIN CONFIGURAR: ejecute «odonto nube-configurar»"
    fi
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
  nube-configurar)
    mkdir -p "$INFRA/rclone" && chmod 700 "$INFRA/rclone"
    cat <<'TXT'

  Copia de respaldos fuera del servidor
  -------------------------------------
  Los respaldos se cifran ANTES de salir del servidor: el proveedor de la nube
  no puede leerlos. Elija dónde guardarlos:

    1) Backblaze B2        (recomendado; 10 GB gratis, luego muy barato)
    2) Cloudflare R2       (10 GB gratis; no cobra por descargar)
    3) Otro: Google Drive, Hetzner Storage Box, Amazon S3, OneDrive… (asistente de rclone)
TXT
    read -rp "  Opción [1-3]: " OP
    case "$OP" in
      1)
        echo "  En backblaze.com: cree un «Bucket» privado y una «Application Key» con acceso a él."
        read -rp "  keyID: " K; read -rsp "  applicationKey: " A; echo; read -rp "  Nombre del bucket: " BUCKET
        "${RCLONE[@]}" config create nube b2 account="$K" key="$A" --obscure >/dev/null ;;
      2)
        echo "  En Cloudflare › R2: cree un bucket y un «API token» de R2 con permiso de lectura y escritura."
        read -rp "  Account ID: " ACC; read -rp "  Access Key ID: " K; read -rsp "  Secret Access Key: " A; echo; read -rp "  Nombre del bucket: " BUCKET
        "${RCLONE[@]}" config create nube s3 provider=Cloudflare access_key_id="$K" secret_access_key="$A" endpoint="https://$ACC.r2.cloudflarestorage.com" acl=private >/dev/null ;;
      3)
        echo "  Se abrirá el asistente de rclone. Cree un remoto llamado EXACTAMENTE: nube"
        echo "  (para Google Drive, rclone le indicará cómo autorizar desde una computadora con navegador)."
        docker run --rm -it -v "$INFRA/rclone:/config/rclone" rclone/rclone:1.68.2 config
        read -rp "  Carpeta o bucket dentro de «nube» donde guardar (ej. odonto-respaldos): " BUCKET ;;
      *) echo "Cancelado."; exit 1 ;;
    esac
    "${RCLONE[@]}" listremotes | grep -qx "nube:" || { echo "✘ No se creó el remoto «nube». Vuelva a intentarlo."; exit 1; }
    read -rp "  ¿Es un servidor NUEVO que debe recuperar respaldos que ya están en la nube? [s/N]: " NUEVO
    if [[ "$NUEVO" =~ ^[sS]$ ]]; then
      read -rsp "  Contraseña de cifrado guardada: " CLAVE; echo
      read -rsp "  Sal guardada: " SAL; echo
    else
      CLAVE=$(openssl rand -base64 30 | tr -d '/+=\n' | cut -c1-32); SAL=$(openssl rand -base64 30 | tr -d '/+=\n' | cut -c1-32)
    fi
    "${RCLONE[@]}" config delete nube-cifrada >/dev/null 2>&1 || true
    "${RCLONE[@]}" config create nube-cifrada crypt remote="nube:${BUCKET}/odonto" password="$CLAVE" password2="$SAL" --obscure >/dev/null
    chmod 600 "$INFRA/rclone/rclone.conf"
    cat <<TXT

  ================================================================
   CLAVES DE CIFRADO — GUÁRDELAS FUERA DEL SERVIDOR
   (gestor de contraseñas, papel en lugar seguro…)
   Sin ellas, los respaldos de la nube NO se pueden abrir.

     Destino:     nube:${BUCKET}/odonto
     Contraseña:  ${CLAVE}
     Sal:         ${SAL}
  ================================================================
TXT
    if [[ "$NUEVO" =~ ^[sS]$ ]]; then
      echo "  Respaldos encontrados en la nube:"; "$0" nube-listar | tail -10
      echo "  Para recuperar uno: odonto nube-recuperar ID  y luego  odonto restaurar ID"
    else
      read -rp "  Escriba GUARDADAS cuando las tenga a salvo: " OK
      [ "$OK" = "GUARDADAS" ] || echo "  ¡Guárdelas igualmente! También están (ofuscadas) en infra/rclone/rclone.conf."
      echo "  Probando: subiendo los respaldos actuales…"
      "$0" nube-subir
    fi
    ;;
  nube-subir)
    "${RCLONE[@]}" listremotes | grep -qx "nube-cifrada:" || { echo "Sin configurar: ejecute «odonto nube-configurar»."; exit 1; }
    mkdir -p "$INFRA/estado"
    docker run --rm -v "$INFRA/rclone:/config/rclone" -v "$INFRA/respaldos:/respaldos:ro" -v "$INFRA/estado:/estado" \
      -v "$INFRA/respaldo-externo.sh:/r.sh:ro" -e RETENCION_EXTERNA_DIAS="${RETENCION_EXTERNA_DIAS:-90}" \
      --entrypoint sh rclone/rclone:1.68.2 /r.sh ahora
    ;;
  nube-listar)
    "${RCLONE[@]}" lsl nube-cifrada: 2>/dev/null | sort -k2,3 || echo "Sin configurar o sin respaldos." ;;
  nube-recuperar)
    F="${2:-}"; [ -n "$F" ] || { echo "Indique el ID (vea «odonto nube-listar»)." >&2; exit 1; }
    "${RCLONE[@]}" copy nube-cifrada: /respaldos --include "odonto-$F.dump" --include "archivos-$F.tar.gz" -P
    [ -f "$INFRA/respaldos/odonto-$F.dump" ] && echo "✔ Descargado. Para volver a ese momento: odonto restaurar $F" || { echo "✘ No se encontró $F en la nube."; exit 1; }
    ;;
  db) "${DC[@]}" exec postgres psql -U odonto -d odonto ;;
  *) ayuda ;;
esac
