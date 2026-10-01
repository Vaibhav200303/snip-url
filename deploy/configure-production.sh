#!/usr/bin/env bash
set -euo pipefail

public_ip="${1:?usage: configure-production.sh PUBLIC_IP}"
app_dir="/opt/snip-url"
env_file="${app_dir}/.env"

install -d -m 0755 "${app_dir}"
if [[ -e "${env_file}" ]]; then
  echo "Production environment already exists; leaving secrets unchanged."
  exit 0
fi

umask 077
admin_api_key="$(openssl rand -hex 32)"
short_code_secret="$(openssl rand -hex 32)"

cat >"${env_file}" <<EOF
ENVIRONMENT=production
PUBLIC_BASE_URL=http://${public_ip}
ADMIN_API_KEY=${admin_api_key}
SHORT_CODE_SECRET=${short_code_secret}
TRUSTED_HOSTS=${public_ip},localhost,127.0.0.1
CORS_ORIGINS=
SNOWFLAKE_WORKER_ID=1
EOF

chmod 0600 "${env_file}"
echo "Production environment created at ${env_file}."
