#!/usr/bin/env bash

set -euo pipefail

AWS_REGION="${AWS_REGION:-ap-southeast-1}"
PARAM_PATH="${PARAM_PATH:-/p160/staging/app}"
GHCR_PARAMETER="${GHCR_PARAMETER:-/p160/staging/ghcr/token}"
GOOGLE_CREDENTIALS_PARAMETER="${GOOGLE_CREDENTIALS_PARAMETER:-/p160/staging/google/service-account-json}"
GHCR_USERNAME="${GHCR_USERNAME:-hyeiu142}"
IMAGE_NAME="${IMAGE_NAME:-ghcr.io/ai20k-build-phase-cohort-3/p-160}"
IMAGE_TAG="${IMAGE_TAG:-development}"
PUBLIC_HOSTNAME="${PUBLIC_HOSTNAME:-staging.alosm.nairyuuu.site}"
DEPLOY_DIR="${DEPLOY_DIR:-/opt/p160-staging}"
COMPOSE_FILE="${DEPLOY_DIR}/docker-compose.staging.yml"
ENV_FILE="${DEPLOY_DIR}/.env.production"
GOOGLE_CREDENTIALS_FILE="${DEPLOY_DIR}/google-service-account.json"

install -d -m 700 "${DEPLOY_DIR}"

env_tmp="$(mktemp "${DEPLOY_DIR}/.env.production.XXXXXX")"
trap 'rm -f "${env_tmp}"' EXIT

aws --region "${AWS_REGION}" ssm get-parameters-by-path \
  --path "${PARAM_PATH}" \
  --recursive \
  --with-decryption \
  --query "Parameters[?Name!='${PARAM_PATH}/GOOGLE_SERVICE_ACCOUNT_JSON'].[Name,Value]" \
  --output text |
  while IFS="$(printf '\t')" read -r parameter_name parameter_value; do
    [ -n "${parameter_name}" ] || continue
    parameter_key="${parameter_name##*/}"
    case "${parameter_key}" in
      GOOGLE_SERVICE_ACCOUNT_JSON|GOOGLE_APPLICATION_CREDENTIALS) continue ;;
    esac
    printf '%s=%s\n' "${parameter_key}" "${parameter_value}"
  done > "${env_tmp}"

google_credentials="$(aws --region "${AWS_REGION}" ssm get-parameter \
  --name "${GOOGLE_CREDENTIALS_PARAMETER}" \
  --with-decryption \
  --query 'Parameter.Value' \
  --output text)"
printf '%s' "${google_credentials}" > "${GOOGLE_CREDENTIALS_FILE}"
chmod 600 "${GOOGLE_CREDENTIALS_FILE}"
printf 'GOOGLE_APPLICATION_CREDENTIALS=%s\n' "${GOOGLE_CREDENTIALS_FILE}" >> "${env_tmp}"

install -m 600 "${env_tmp}" "${ENV_FILE}"

ghcr_token="$(aws --region "${AWS_REGION}" ssm get-parameter \
  --name "${GHCR_PARAMETER}" \
  --with-decryption \
  --query 'Parameter.Value' \
  --output text)"
printf '%s' "${ghcr_token}" |
  docker login ghcr.io --username "${GHCR_USERNAME}" --password-stdin >/dev/null

docker compose -f "${COMPOSE_FILE}" pull
docker compose -f "${COMPOSE_FILE}" up -d --remove-orphans
docker logout ghcr.io >/dev/null

curl --fail --silent --show-error --location --max-time 60 \
  --resolve "${PUBLIC_HOSTNAME}:80:127.0.0.1" \
  --resolve "${PUBLIC_HOSTNAME}:443:127.0.0.1" \
  "http://${PUBLIC_HOSTNAME}/health"
printf '\n'
docker compose -f "${COMPOSE_FILE}" ps
