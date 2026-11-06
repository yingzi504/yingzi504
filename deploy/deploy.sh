#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if [ -f "$SCRIPT_DIR/deploy.env" ]; then
  set -a
  # shellcheck disable=SC1091
  source "$SCRIPT_DIR/deploy.env"
  set +a
fi

REMOTE_USER="${REMOTE_USER:-root}"
REMOTE_HOST="${REMOTE_HOST:-47.110.226.47}"
REMOTE_PORT="${REMOTE_PORT:-22}"
REMOTE_PASSWORD="${REMOTE_PASSWORD:-CHANGE_ME_ROOT_PASSWORD}"
SSH_PRIVATE_KEY_FILE="${SSH_PRIVATE_KEY_FILE:-}"
REMOTE_BASE_DIR="${REMOTE_BASE_DIR:-/root/projects}"
APP_NAME="${APP_NAME:-cv-agent}"
HTTP_PORT="${HTTP_PORT:-80}"
PYTHON_IMAGE="${PYTHON_IMAGE:-swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/library/python:3.12-slim}"
NODE_IMAGE="${NODE_IMAGE:-swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/library/node:24-alpine}"
NGINX_IMAGE="${NGINX_IMAGE:-swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/library/nginx:alpine}"
PNPM_VERSION="${PNPM_VERSION:-9.15.9}"
APT_MIRROR="${APT_MIRROR:-http://mirrors.aliyun.com/debian}"
APT_SECURITY_MIRROR="${APT_SECURITY_MIRROR:-http://mirrors.aliyun.com/debian-security}"
PIP_INDEX_URL="${PIP_INDEX_URL:-https://mirrors.aliyun.com/pypi/simple/}"
NPM_REGISTRY="${NPM_REGISTRY:-https://registry.npmmirror.com}"
EMPTY_OPTIONAL_ARG="__CV_AGENT_EMPTY_OPTIONAL_ARG__"
PIP_INDEX_URL_ARG="${PIP_INDEX_URL:-$EMPTY_OPTIONAL_ARG}"
NPM_REGISTRY_ARG="${NPM_REGISTRY:-$EMPTY_OPTIONAL_ARG}"

RELEASE_ID="$(date +%Y%m%d%H%M%S)"
ARCHIVE_NAME="${APP_NAME}-${RELEASE_ID}.tar.gz"
LOCAL_ARCHIVE="${TMPDIR:-/tmp}/${ARCHIVE_NAME}"
REMOTE_APP_DIR="${REMOTE_BASE_DIR%/}/${APP_NAME}"
REMOTE_INCOMING_DIR="${REMOTE_APP_DIR}/incoming"
REMOTE_RELEASES_DIR="${REMOTE_APP_DIR}/releases"
REMOTE_ARCHIVE="${REMOTE_INCOMING_DIR}/${ARCHIVE_NAME}"

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required local command: $1" >&2
    exit 1
  fi
}

use_password_auth() {
  [ -n "$REMOTE_PASSWORD" ] && [ "$REMOTE_PASSWORD" != "CHANGE_ME_ROOT_PASSWORD" ]
}

ssh_cmd() {
  if use_password_auth; then
    if ! command -v sshpass >/dev/null 2>&1; then
      echo "REMOTE_PASSWORD is set, but sshpass is not installed locally." >&2
      echo "Install sshpass or configure SSH key login, then rerun this script." >&2
      exit 1
    fi
    sshpass -p "$REMOTE_PASSWORD" ssh "${SSH_OPTS[@]}" "$REMOTE_USER@$REMOTE_HOST" "$@"
  else
    ssh "${SSH_OPTS[@]}" "$REMOTE_USER@$REMOTE_HOST" "$@"
  fi
}

scp_upload() {
  if use_password_auth; then
    sshpass -p "$REMOTE_PASSWORD" scp "${SCP_OPTS[@]}" "$1" "$REMOTE_USER@$REMOTE_HOST:$2"
  else
    scp "${SCP_OPTS[@]}" "$1" "$REMOTE_USER@$REMOTE_HOST:$2"
  fi
}

cleanup() {
  rm -f "$LOCAL_ARCHIVE"
}
trap cleanup EXIT

require_command tar
require_command ssh
require_command scp

SSH_OPTS=(-p "$REMOTE_PORT" -o StrictHostKeyChecking=accept-new)
SCP_OPTS=(-P "$REMOTE_PORT" -o StrictHostKeyChecking=accept-new)
if [ -n "$SSH_PRIVATE_KEY_FILE" ]; then
  if [ ! -f "$SSH_PRIVATE_KEY_FILE" ]; then
    echo "SSH private key file does not exist: $SSH_PRIVATE_KEY_FILE" >&2
    exit 1
  fi
  SSH_OPTS+=(-i "$SSH_PRIVATE_KEY_FILE" -o IdentitiesOnly=yes)
  SCP_OPTS+=(-i "$SSH_PRIVATE_KEY_FILE" -o IdentitiesOnly=yes)
fi

echo "==> Packaging project: $REPO_ROOT"
(
  cd "$REPO_ROOT"
tar \
    --exclude='frontend/node_modules' \
    --exclude='frontend/dist' \
    --exclude='frontend/.vite' \
    --exclude='frontend/.env.*' \
    --exclude='frontend/*.log' \
    --exclude='frontend/*.png' \
    --exclude='frontend/*.xml' \
    --exclude='backend/.venv' \
    --exclude='backend/.env' \
    --exclude='backend/venv' \
    --exclude='backend/env' \
    --exclude='backend/ENV' \
    --exclude='backend/__pycache__' \
    --exclude='backend/.pytest_cache' \
    --exclude='backend/uploads' \
    --exclude='backend/output' \
    --exclude='backend/data/*.db' \
    --exclude='backend/data/*.sqlite' \
    --exclude='backend/data/*.sqlite3' \
    -czf "$LOCAL_ARCHIVE" \
    docker-compose.yml \
    backend \
    frontend
)

echo "==> Preparing remote directories: ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_APP_DIR}"
ssh_cmd mkdir -p "$REMOTE_INCOMING_DIR" "$REMOTE_RELEASES_DIR"

echo "==> Uploading archive: $ARCHIVE_NAME"
scp_upload "$LOCAL_ARCHIVE" "$REMOTE_ARCHIVE"

echo "==> Deploying release on remote server"
ssh_cmd bash -s -- \
  "$REMOTE_BASE_DIR" \
  "$APP_NAME" \
  "$RELEASE_ID" \
  "$REMOTE_ARCHIVE" \
  "$HTTP_PORT" \
  "$PYTHON_IMAGE" \
  "$NODE_IMAGE" \
  "$NGINX_IMAGE" \
  "$PNPM_VERSION" \
  "$APT_MIRROR" \
  "$APT_SECURITY_MIRROR" \
  "$PIP_INDEX_URL_ARG" \
  "$NPM_REGISTRY_ARG" <<'REMOTE_SCRIPT'
set -euo pipefail

REMOTE_BASE_DIR="$1"
APP_NAME="$2"
RELEASE_ID="$3"
REMOTE_ARCHIVE="$4"
HTTP_PORT="$5"
PYTHON_IMAGE="$6"
NODE_IMAGE="$7"
NGINX_IMAGE="$8"
PNPM_VERSION="$9"
APT_MIRROR="${10}"
APT_SECURITY_MIRROR="${11}"
EMPTY_OPTIONAL_ARG="__CV_AGENT_EMPTY_OPTIONAL_ARG__"
PIP_INDEX_URL="${12:-$EMPTY_OPTIONAL_ARG}"
NPM_REGISTRY="${13:-$EMPTY_OPTIONAL_ARG}"

if [ "$PIP_INDEX_URL" = "$EMPTY_OPTIONAL_ARG" ]; then
  PIP_INDEX_URL=""
fi

if [ "$NPM_REGISTRY" = "$EMPTY_OPTIONAL_ARG" ]; then
  NPM_REGISTRY=""
fi

APP_DIR="${REMOTE_BASE_DIR%/}/${APP_NAME}"
RELEASES_DIR="$APP_DIR/releases"
RELEASE_DIR="$RELEASES_DIR/$RELEASE_ID"
SHARED_DIR="$APP_DIR/shared"
CURRENT_LINK="$APP_DIR/current"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is not installed on the remote server." >&2
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "Docker Compose v2 plugin is not installed on the remote server." >&2
  exit 1
fi

mkdir -p \
  "$RELEASE_DIR" \
  "$SHARED_DIR/backend/data" \
  "$SHARED_DIR/backend/uploads" \
  "$SHARED_DIR/backend/output" \
  "$SHARED_DIR/backend/templates" \
  "$SHARED_DIR/backend/paddleocr" \
  "$SHARED_DIR/backend/paddle"

tar -xzf "$REMOTE_ARCHIVE" -C "$RELEASE_DIR"

if [ ! -f "$SHARED_DIR/backend/.env" ]; then
  cp "$RELEASE_DIR/backend/.env.example" "$SHARED_DIR/backend/.env"
  echo "Created backend env file: $SHARED_DIR/backend/.env"
else
  echo "Preserving existing production env file: $SHARED_DIR/backend/.env"
fi

if [ -d "$RELEASE_DIR/backend/data" ]; then
  cp -an "$RELEASE_DIR/backend/data/." "$SHARED_DIR/backend/data/" 2>/dev/null || true
fi

if [ -d "$RELEASE_DIR/backend/templates" ]; then
  # Preserve server-side custom templates, but always refresh the four
  # application-owned built-ins so template changes ship with each release.
  cp -an "$RELEASE_DIR/backend/templates/." "$SHARED_DIR/backend/templates/" 2>/dev/null || true
  for template in \
    Onepager_Template_CN.pptx \
    Onepager_Template_EN.pptx \
    New_Template_IAV_Resume_CN.pptx \
    New_Template_IAV_Resume_EN.pptx
  do
    if [ -f "$RELEASE_DIR/backend/templates/$template" ]; then
      cp -f "$RELEASE_DIR/backend/templates/$template" "$SHARED_DIR/backend/templates/$template"
    fi
  done
  echo "Synced built-in PPT templates from release."
fi

missing_templates=""
for template in \
  Onepager_Template_CN.pptx \
  Onepager_Template_EN.pptx \
  New_Template_IAV_Resume_CN.pptx \
  New_Template_IAV_Resume_EN.pptx
do
  if [ ! -f "$SHARED_DIR/backend/templates/$template" ]; then
    missing_templates="${missing_templates} ${template}"
  fi
done

if [ -n "$missing_templates" ]; then
  echo "WARNING: Missing built-in PPT templates:${missing_templates}" >&2
  echo "CV generation needs these exact filenames in $SHARED_DIR/backend/templates." >&2
fi

cd "$RELEASE_DIR"
APP_DATA_DIR="$SHARED_DIR" \
BACKEND_ENV_FILE="$SHARED_DIR/backend/.env" \
HTTP_PORT="$HTTP_PORT" \
PYTHON_IMAGE="$PYTHON_IMAGE" \
NODE_IMAGE="$NODE_IMAGE" \
NGINX_IMAGE="$NGINX_IMAGE" \
PNPM_VERSION="$PNPM_VERSION" \
APT_MIRROR="$APT_MIRROR" \
APT_SECURITY_MIRROR="$APT_SECURITY_MIRROR" \
PIP_INDEX_URL="$PIP_INDEX_URL" \
NPM_REGISTRY="$NPM_REGISTRY" \
docker compose --project-name "$APP_NAME" --env-file "$SHARED_DIR/backend/.env" up -d --build --remove-orphans

APP_DATA_DIR="$SHARED_DIR" BACKEND_ENV_FILE="$SHARED_DIR/backend/.env" HTTP_PORT="$HTTP_PORT" docker compose --project-name "$APP_NAME" --env-file "$SHARED_DIR/backend/.env" ps

if ! command -v curl >/dev/null 2>&1; then
  echo "curl is required on the remote server for the deployment health check." >&2
  exit 1
fi

echo "Waiting for health check..."
health_ok=false
for _ in $(seq 1 30); do
  if curl -fsS "http://127.0.0.1:${HTTP_PORT}/health" >/dev/null 2>&1; then
    health_ok=true
    break
  fi
  sleep 2
done

if [ "$health_ok" != true ]; then
  echo "Health check did not pass within 60 seconds." >&2
  APP_DATA_DIR="$SHARED_DIR" BACKEND_ENV_FILE="$SHARED_DIR/backend/.env" HTTP_PORT="$HTTP_PORT" \
    docker compose --project-name "$APP_NAME" --env-file "$SHARED_DIR/backend/.env" ps >&2 || true
  APP_DATA_DIR="$SHARED_DIR" BACKEND_ENV_FILE="$SHARED_DIR/backend/.env" HTTP_PORT="$HTTP_PORT" \
    docker compose --project-name "$APP_NAME" --env-file "$SHARED_DIR/backend/.env" \
    logs --tail=100 backend frontend >&2 || true
  exit 1
fi

if ! curl -fsS "http://127.0.0.1:${HTTP_PORT}/" >/dev/null 2>&1; then
  echo "Frontend root check failed after backend health passed." >&2
  exit 1
fi

ln -sfn "$RELEASE_DIR" "$CURRENT_LINK"
echo "Backend health and frontend root checks passed."
REMOTE_SCRIPT

echo "==> Deployment complete"
BASE_URL="http://${REMOTE_HOST}"
if [ "$HTTP_PORT" != "80" ]; then
  BASE_URL="${BASE_URL}:${HTTP_PORT}"
fi
echo "App URL: ${BASE_URL}/"
echo "API docs: ${BASE_URL}/docs"
