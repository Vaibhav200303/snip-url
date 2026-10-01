#!/usr/bin/env bash
set -euo pipefail

short_code="${1:?usage: verify-production.sh SHORT_CODE PUBLIC_HOST}"
public_host="${2:?usage: verify-production.sh SHORT_CODE PUBLIC_HOST}"
app_dir="/opt/snip-url"
admin_base="http://127.0.0.1:8080"
api_key="$(sed -n 's/^ADMIN_API_KEY=//p' "${app_dir}/.env")"

status() {
  curl --silent --show-error --output /dev/null --write-out '%{http_code}' "$@"
}

admin_page="$(status "${admin_base}/admin")"
detail="$(status --header "X-API-Key: ${api_key}" "${admin_base}/api/v1/urls/${short_code}")"
listing="$(status --header "X-API-Key: ${api_key}" "${admin_base}/api/v1/urls?limit=10")"
public_admin="$(status --header "Host: ${public_host}" "http://127.0.0.1/admin")"
public_protected="$(status --header "Host: ${public_host}" \
  --header "X-API-Key: ${api_key}" "http://127.0.0.1/api/v1/urls/${short_code}")"

today="$(date -u +%F)"
analytics=""
for _attempt in $(seq 1 15); do
  analytics="$(curl --silent --show-error --header "X-API-Key: ${api_key}" \
    "${admin_base}/api/v1/urls/${short_code}/analytics?from=${today}&to=${today}")"
  if grep -Eq '"total_clicks"[[:space:]]*:[[:space:]]*[1-9]' <<<"${analytics}"; then
    break
  fi
  sleep 2
done

cache_key="$(cd "${app_dir}" && docker compose exec -T redis \
  redis-cli EXISTS "url:${short_code}" | tr -d '\r')"
disable="$(status --request PATCH --header "X-API-Key: ${api_key}" \
  --header 'Content-Type: application/json' --data '{"is_enabled":false}' \
  "${admin_base}/api/v1/urls/${short_code}")"
disabled_redirect="$(status --header "Host: ${public_host}" \
  "http://127.0.0.1/${short_code}")"
reenable="$(status --request PATCH --header "X-API-Key: ${api_key}" \
  --header 'Content-Type: application/json' --data '{"is_enabled":true}' \
  "${admin_base}/api/v1/urls/${short_code}")"

[[ "${admin_page}" == "200" && "${detail}" == "200" && "${listing}" == "200" ]]
[[ "${public_admin}" == "404" && "${public_protected}" == "404" ]]
[[ "${cache_key}" == "1" && "${disable}" == "200" ]]
[[ "${disabled_redirect}" == "410" && "${reenable}" == "200" ]]
grep -Eq '"total_clicks"[[:space:]]*:[[:space:]]*[1-9]' <<<"${analytics}"

printf '{"admin_page":%s,"detail":%s,"list":%s,"public_admin":%s,' \
  "${admin_page}" "${detail}" "${listing}" "${public_admin}"
printf '"public_protected_with_valid_key":%s,"cache_key":%s,' \
  "${public_protected}" "${cache_key}"
printf '"disable":%s,"disabled_redirect":%s,"reenable":%s,"analytics":%s}\n' \
  "${disable}" "${disabled_redirect}" "${reenable}" "${analytics}"
