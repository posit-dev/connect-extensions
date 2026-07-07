#!/usr/bin/env bash
# Run the integration test for a Node.js extension against a local Connect.
#
# Published Connect images do not include a Node.js runtime, so a plain
# `with-connect` run cannot execute Node.js content. This script starts Connect,
# installs Node into the running container, enables Node in Connect's config, and
# restarts Connect so it loads Node before the extension is deployed. It mirrors
# the provisioning the CI action does for nodejs extensions.
#
# Usage: nodejs-integration-test.sh <connect-version> <extension-name>
set -euo pipefail

CONNECT_VERSION="${1:?connect version required}"
EXTENSION_NAME="${2:?extension name required}"

: "${WITH_CONNECT:=with-connect}"
: "${LICENSE_FILE:=./license.lic}"
: "${UV:=uv}"
: "${PYTEST_ARGS:=-s}"
: "${NODE_VERSION:=24.14.0}"

cd "$(dirname "$0")"
mkdir -p reports logs

# Start Connect without Node. with-connect prints CONNECT_API_KEY,
# CONNECT_SERVER, and CONTAINER_ID for us to eval into this shell.
CONNECT_API_KEY=""
CONNECT_SERVER=""
CONTAINER_ID=""
eval "$("$WITH_CONNECT" --version "$CONNECT_VERSION" --license "$LICENSE_FILE" \
  -e CONNECT_SERVER_EMAILPROVIDER=None \
  -e CONNECT_APPLICATIONS_PACKAGEAUDITINGENABLED=true)"

# Always stop Connect on exit, however we exit.
trap '"$WITH_CONNECT" --stop "$CONTAINER_ID" >/dev/null 2>&1 || true' EXIT

# Match the Node.js build to the container's architecture. On Apple Silicon the
# Connect container runs arm64, where a linux-x64 Node.js build cannot execute.
CONTAINER_ARCH="$(docker exec "$CONTAINER_ID" uname -m)"
case "$CONTAINER_ARCH" in
  x86_64) NODE_ARCH="x64" ;;
  aarch64) NODE_ARCH="arm64" ;;
  *) echo "Unsupported container architecture: $CONTAINER_ARCH"; exit 1 ;;
esac

# Download and unpack Node on this machine, then copy it into the container
# (the Connect images do not reliably include curl/tar/xz).
curl -fsSL "https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-${NODE_ARCH}.tar.xz" -o /tmp/node.tar.xz
rm -rf "/tmp/node/${NODE_VERSION}"
mkdir -p "/tmp/node/${NODE_VERSION}"
tar -xJf /tmp/node.tar.xz -C "/tmp/node/${NODE_VERSION}" --strip-components=1
docker exec "$CONTAINER_ID" mkdir -p /opt/node
docker cp "/tmp/node/${NODE_VERSION}" "$CONTAINER_ID:/opt/node/${NODE_VERSION}"

# Turn Node on in Connect's config and restart so it loads. Connect validates the
# configured executable at startup, so Node must be in place before the restart.
docker exec "$CONTAINER_ID" sh -c \
  "printf '\n[NodeJs]\nEnabled = true\nExecutable = /opt/node/${NODE_VERSION}/bin/node\n' >> /etc/rstudio-connect/rstudio-connect.gcfg"
docker restart "$CONTAINER_ID"

echo "Waiting for Connect to restart with Node enabled..."
for _ in $(seq 1 45); do
  if curl -fsS "${CONNECT_SERVER}/__api__/server_settings" >/dev/null 2>&1; then
    break
  fi
  sleep 2
done
if ! curl -fsS "${CONNECT_SERVER}/__api__/server_settings" >/dev/null 2>&1; then
  echo "Connect did not come back up after enabling Node:"
  docker logs "$CONTAINER_ID" 2>&1 | tail -60
  exit 1
fi

# Run the tests against the provisioned Connect.
export CONNECT_SERVER CONNECT_API_KEY
"$UV" run tests/posit/connect/set_bootstrap_admin_email.py
EXTENSION_NAME="$EXTENSION_NAME" BUNDLE_BASE_PATH="$PWD/bundles" \
  "$UV" run pytest $PYTEST_ARGS --junit-xml="./reports/${CONNECT_VERSION}.xml" 2>&1 \
  | tee "./logs/${CONNECT_VERSION}.log"
