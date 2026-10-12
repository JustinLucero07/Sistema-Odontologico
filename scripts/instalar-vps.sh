#!/usr/bin/env bash
# Instalación completa en un VPS nuevo (Ubuntu 22.04/24.04 o Debian 12).
#
#   sudo bash scripts/instalar-vps.sh
#
# Hace, en orden:
#   1. Actualiza el sistema e instala lo básico (git, firewall, fail2ban,
#      actualizaciones de seguridad automáticas).
#   2. Crea memoria swap si el servidor tiene poca RAM (la compilación la necesita).
#   3. Instala Docker.
#   4. Abre solo los puertos 22 (SSH), 80 y 443.
#   5. Crea infra/.env.prod con claves aleatorias (pregunta el dominio y el correo).
#   6. Comprueba que el dominio apunte a este servidor.
#   7. Compila y arranca todo, con HTTPS automático.
#   8. Instala el comando «odonto» para administrar el servidor.
#
# Se puede volver a ejecutar sin riesgo: lo que ya está hecho se salta.

set -euo pipefail

VERDE='\033[1;32m'; AMARILLO='\033[1;33m'; ROJO='\033[1;31m'; AZUL='\033[1;36m'; NADA='\033[0m'
paso()  { echo -e "\n${AZUL}==> $*${NADA}"; }
ok()    { echo -e "${VERDE}✔ $*${NADA}"; }
aviso() { echo -e "${AMARILLO}! $*${NADA}"; }
error() { echo -e "${ROJO}✘ $*${NADA}" >&2; exit 1; }

[ "$(id -u)" -eq 0 ] || error "Ejecútelo como administrador: sudo bash $0"

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INFRA="$RAIZ/infra"
ENV="$INFRA/.env.prod"
COMPOSE=(docker compose -f "$INFRA/docker-compose.prod.yml" --env-file "$ENV")

[ -f "$INFRA/docker-compose.prod.yml" ] || error "No encuentro infra/docker-compose.prod.yml. Ejecute el script desde la carpeta del sistema."

. /etc/os-release
case "${ID:-}" in
  ubuntu|debian) ;;
  *) aviso "Probado en Ubuntu y Debian. Su sistema es ${PRETTY_NAME:-desconocido}: se intentará igual." ;;
esac

# ---------------------------------------------------------------------------
paso "1/8 Actualizando el sistema"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get upgrade -y -qq
apt-get install -y -qq curl git ufw fail2ban unattended-upgrades ca-certificates dnsutils openssl >/dev/null
dpkg-reconfigure -f noninteractive unattended-upgrades >/dev/null 2>&1 || true
systemctl enable --now fail2ban >/dev/null 2>&1 || true
ok "Sistema al día, fail2ban y actualizaciones de seguridad automáticas activos"

# ---------------------------------------------------------------------------
paso "2/8 Memoria"
RAM_MB=$(awk '/MemTotal/ {print int($2/1024)}' /proc/meminfo)
if [ "$RAM_MB" -lt 3500 ] && ! swapon --show | grep -q .; then
  fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile >/dev/null && swapon /swapfile
  grep -q '/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
  ok "RAM de ${RAM_MB} MB: se creó una swap de 2 GB"
else
  ok "RAM de ${RAM_MB} MB: no hace falta swap extra"
fi

# ---------------------------------------------------------------------------
paso "3/8 Docker"
if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sh >/dev/null
  systemctl enable --now docker
  ok "Docker instalado"
else
  ok "Docker ya estaba instalado ($(docker --version | cut -d, -f1))"
fi
docker compose version >/dev/null 2>&1 || error "Falta el plugin «docker compose». Instálelo: apt-get install docker-compose-plugin"

# ---------------------------------------------------------------------------
paso "4/8 Firewall"
ufw allow OpenSSH >/dev/null
ufw allow 80/tcp >/dev/null
ufw allow 443/tcp >/dev/null
ufw --force enable >/dev/null
ok "Abiertos solo SSH, 80 y 443 (la base de datos no queda expuesta)"

# ---------------------------------------------------------------------------
paso "5/8 Configuración (.env.prod)"
clave() { openssl rand -base64 48 | tr -d '/+=\n' | cut -c1-56; }
if [ ! -f "$ENV" ]; then
  DOMINIO="${DOMINIO:-}"
  CORREO="${CORREO_TLS:-}"
  while [ -z "$DOMINIO" ]; do read -rp "Dominio donde funcionará el sistema (ej. app.miclinica.com): " DOMINIO; done
  DOMINIO="${DOMINIO#http://}"; DOMINIO="${DOMINIO#https://}"; DOMINIO="${DOMINIO%%/*}"
  while [ -z "$CORREO" ]; do read -rp "Correo para avisos del certificado HTTPS: " CORREO; done
  read -rp "Nombre de su empresa (sale en los Términos de uso) [el proveedor del sistema]: " PROVEEDOR || true
  PROVEEDOR="${PROVEEDOR:-el proveedor del sistema}"
  WORKERS=2; [ "$RAM_MB" -ge 3800 ] && WORKERS=4
  umask 077
  cat > "$ENV" <<EOF
# Generado por instalar-vps.sh el $(date '+%Y-%m-%d %H:%M').
# Contiene las claves del sistema: no lo comparta ni lo suba a un repositorio.
DOMINIO=$DOMINIO
CORREO_TLS=$CORREO
POSTGRES_PASSWORD=$(clave)
JWT_SECRET_KEY=$(clave)
RETENCION_DIAS=30
HORA_RESPALDO=02
PROVIDER_NAME="$PROVEEDOR"
PROVIDER_TAX_ID=
PROVIDER_EMAIL=
WEB_WORKERS=$WORKERS
WHATSAPP_TOKEN=
WHATSAPP_PHONE_NUMBER_ID=
ANTHROPIC_API_KEY=
EOF
  ok "Creado infra/.env.prod con claves aleatorias (guárdelo en un lugar seguro)"
else
  ok "infra/.env.prod ya existe: se conserva"
fi
set -a; . "$ENV"; set +a

# ---------------------------------------------------------------------------
paso "6/8 Comprobando el dominio ${DOMINIO}"
IP_SERVIDOR=$(curl -fsS4 --max-time 10 https://api.ipify.org || true)
IP_DOMINIO=$(dig +short A "$DOMINIO" | tail -n1)
if [ -n "$IP_SERVIDOR" ] && [ "$IP_SERVIDOR" = "$IP_DOMINIO" ]; then
  ok "${DOMINIO} apunta a este servidor (${IP_SERVIDOR})"
else
  aviso "${DOMINIO} apunta a «${IP_DOMINIO:-nada}» y este servidor es ${IP_SERVIDOR:-desconocido}."
  aviso "Cree un registro DNS tipo A: ${DOMINIO} → ${IP_SERVIDOR}. Sin eso no habrá certificado HTTPS."
  if [ -t 0 ]; then
    read -rp "¿Continuar de todos modos? [s/N] " r
    [[ "$r" =~ ^[sS]$ ]] || error "Instalación detenida. Configure el DNS y vuelva a ejecutar el script."
  fi
fi

# ---------------------------------------------------------------------------
paso "7/8 Compilando y arrancando (la primera vez tarda 5-10 minutos)"
mkdir -p "$INFRA/respaldos"
"${COMPOSE[@]}" up -d --build
echo -n "Esperando a que el sistema responda"
for i in $(seq 1 90); do
  if curl -fsS --max-time 5 "https://${DOMINIO}/api/v1/health" >/dev/null 2>&1; then
    echo; ok "Funcionando en https://${DOMINIO}"; LISTO=1; break
  fi
  echo -n "."; sleep 5
done
if [ -z "${LISTO:-}" ]; then
  echo
  aviso "Aún no responde por HTTPS. Suele ser el DNS o el certificado. Revise con: odonto logs caddy"
fi

# ---------------------------------------------------------------------------
paso "8/8 Comando de administración"
chmod +x "$INFRA/odonto.sh"
ln -sf "$INFRA/odonto.sh" /usr/local/bin/odonto
ok "Instalado: escriba «odonto» para ver lo que puede hacer"

cat <<EOF

$(echo -e "${VERDE}Instalación terminada.${NADA}")

Siguiente paso, crear el primer cliente:

  Odontólogo que trabaja solo:
    odonto nueva-clinica --nombre "Consultorio Dra. Ana Paz" \\
      --admin-email ana@correo.com --admin-nombre Ana --admin-apellido Paz \\
      --odontologo --registro "MSP-12345"

  Clínica con equipo:
    odonto nueva-clinica --nombre "Clínica Dental Sonrisa" \\
      --admin-email admin@sonrisa.ec --admin-nombre Ana --admin-apellido Pérez

El comando muestra una contraseña temporal. Al entrar en https://${DOMINIO}
el cliente la cambia y sigue el asistente de bienvenida (logo, colores,
horario y módulos).

Respaldos: cada día a las ${HORA_RESPALDO:-02}:00 en ${INFRA}/respaldos.
Cópielos fuera del servidor (ver docs/INSTALACION_PRODUCCION.md, paso 7).
EOF
