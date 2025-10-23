#!/bin/bash
set -euo pipefail

LOG_FILE="/var/log/mcp-oci-cloud-init.log"
exec > >(tee -a "$${LOG_FILE}") 2>&1

echo "[cloud-init] Starting MCP-OCI streamable deployment prep"

PKG_MANAGER="dnf"
if ! command -v dnf >/dev/null 2>&1; then
  PKG_MANAGER="yum"
fi

$${PKG_MANAGER} -y install oracle-epel-release-el9 || true
$${PKG_MANAGER} -y install git docker docker-compose-plugin firewalld jq unzip curl || true

if ! command -v oci >/dev/null 2>&1; then
  curl -sSL https://raw.githubusercontent.com/oracle/oci-cli/master/scripts/install/install.sh -o /tmp/oci-cli-install.sh
  chmod +x /tmp/oci-cli-install.sh
  /tmp/oci-cli-install.sh --accept-all-defaults --install-dir /usr/local/lib/oci-cli --exec-dir /usr/local/bin --script-dir /usr/local/bin
  rm -f /tmp/oci-cli-install.sh
fi

systemctl enable --now docker
systemctl enable --now firewalld

usermod -aG docker opc || true

ports=(
  7001 7002 7003 7004 7005 7006 7007 7008 7009 7010 7011
  8000 8001 8002 8003 8004 8005 8006 8007 8008 8009 8010 8011
)

ALLOWED_SOURCE="${authorized_source}"

if [[ -n "$ALLOWED_SOURCE" ]]; then
  for port in "$${ports[@]}"; do
    firewall-cmd --permanent --add-rich-rule="rule family=ipv4 source address=$ALLOWED_SOURCE port port=$${port} protocol=tcp accept" || true
  done
else
  for port in "$${ports[@]}"; do
    firewall-cmd --permanent --add-port="$${port}/tcp" || true
  done
fi
firewall-cmd --reload || true

runuser -l opc -c 'mkdir -p ~/mcp-oci-cloud'
runuser -l opc -c 'if [ ! -d ~/mcp-oci-cloud/repo ]; then git clone https://github.com/adibirzu/mcp-oci.git ~/mcp-oci-cloud/repo; fi'
runuser -l opc -c 'cd ~/mcp-oci-cloud/repo && docker build -t mcp-oci:latest .'

cat <<'COMPOSE' >/home/opc/mcp-oci-cloud/docker-compose.yml
version: "3.9"
services:
  mcp-oci:
    image: mcp-oci:latest
    restart: unless-stopped
    env_file:
      - .env
    environment:
      MCP_TRANSPORT: streamable-http
      MCP_HOST: 0.0.0.0
    ports:
      - "7001:7001"
      - "7002:7002"
      - "7003:7003"
      - "7004:7004"
      - "7005:7005"
      - "7006:7006"
      - "7007:7007"
      - "7008:7008"
      - "7009:7009"
      - "7010:7010"
      - "7011:7011"
      - "8000:8000"
      - "8001:8001"
      - "8002:8002"
      - "8003:8003"
      - "8004:8004"
      - "8005:8005"
      - "8006:8006"
      - "8007:8007"
      - "8008:8008"
      - "8009:8009"
      - "8010:8010"
      - "8011:8011"
    volumes:
      - ./logs:/var/log/mcp
COMPOSE

cat <<'BOOTSTRAP' >/home/opc/mcp-oci-cloud/bootstrap-mcp.sh
#!/usr/bin/env bash
set -euo pipefail

WORKDIR="$(cd "$(dirname "$${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$${WORKDIR}/.env"

echo "[bootstrap] Preparing MCP-OCI environment file at $${ENV_FILE}"
if [[ ! -f "$${ENV_FILE}" ]]; then
  touch "$${ENV_FILE}"
  chmod 600 "$${ENV_FILE}"
  while true; do
    read -r -p "Enter env key=value (blank to finish): " line || true
    [[ -z "$${line}" ]] && break
    if [[ "$${line}" != *=* ]]; then
      echo "Invalid entry. Use KEY=VALUE format."
      continue
    fi
    if grep -q "^$${line%%=*}=" "$${ENV_FILE}"; then
      sed -i.bak "s|^$${line%%=*}=.*|$${line}|" "$${ENV_FILE}"
      rm -f "$${ENV_FILE}.bak"
    else
      echo "$${line}" >>"$${ENV_FILE}"
    fi
  done
fi

echo "[bootstrap] Ensuring streamable transport defaults"
grep -q "^MCP_TRANSPORT=" "$${ENV_FILE}" || echo "MCP_TRANSPORT=streamable-http" >>"$${ENV_FILE}"
grep -q "^MCP_HOST=" "$${ENV_FILE}" || echo "MCP_HOST=0.0.0.0" >>"$${ENV_FILE}"

echo "[bootstrap] Starting containers via docker compose"
cd "$${WORKDIR}"
docker compose down || true
docker compose up -d

echo "[bootstrap] Deployment finished. Active containers:"
docker compose ps
BOOTSTRAP

chown -R opc:opc /home/opc/mcp-oci-cloud
chmod +x /home/opc/mcp-oci-cloud/bootstrap-mcp.sh

echo "[cloud-init] Completed MCP-OCI streamable preparation"
