#!/usr/bin/env bash
# BSidesOK 2026 Lab 5 — Podman startup script
set -euo pipefail

IMAGE="${OPENCLAW_IMAGE:-ghcr.io/openclaw/openclaw:latest}"
CONTAINER="openclaw-lab5"
LAB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "[lab5] Starting OpenClaw container via Podman"
echo "[lab5] Lab directory: ${LAB_DIR}"
echo "[lab5] Image: ${IMAGE}"

if podman container exists "${CONTAINER}" 2>/dev/null; then
    echo "[lab5] Removing existing container: ${CONTAINER}"
    podman rm -f "${CONTAINER}"
fi

# --add-host provides host.docker.internal on Linux for Ollama access
podman run -d \
    --name "${CONTAINER}" \
    -p 127.0.0.1:18789:18789 \
    -e OPENCLAW_HOME=/home/node/.openclaw \
    -e OPENCLAW_PORT=18789 \
    -v "${LAB_DIR}/workspace:/workspace:ro,Z" \
    -v "${LAB_DIR}/state:/lab5/state:Z" \
    -v "${LAB_DIR}/config:/home/node/.openclaw:Z" \
    --add-host=host.docker.internal:host-gateway \
    --restart unless-stopped \
    "${IMAGE}"

echo "[lab5] Container started. Logs:"
podman logs -f "${CONTAINER}" &

echo ""
echo "[lab5] Waiting for gateway to be ready..."
for i in $(seq 1 20); do
    if curl -sf http://localhost:18789/healthz >/dev/null 2>&1; then
        echo "[lab5] Gateway ready at http://localhost:18789"
        echo "[lab5] Canvas UI: http://localhost:18789/__openclaw__/canvas/"
        echo "[lab5] Auth token: $(grep -o '\"token\": \"[^\"]*\"' \
            "${LAB_DIR}/config/.openclaw/openclaw.json" 2>/dev/null | \
            cut -d'"' -f4 || echo 'check config/.openclaw/openclaw.json')"
        break
    fi
    sleep 1
done
