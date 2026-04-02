#!/usr/bin/env bash
set -euo pipefail

IMAGE="${OPENCLAW_IMAGE:-ghcr.io/openclaw/openclaw:latest}"
NAME="${OPENCLAW_CONTAINER_NAME:-openclaw-lab5}"

podman rm -f "$NAME" >/dev/null 2>&1 || true

podman run -d   --name "$NAME"   -p 127.0.0.1:18789:18789   -e OPENCLAW_HOME=/home/node/.openclaw   -e OPENCLAW_PORT=18789   -v "$(pwd)/workspace:/workspace:Z"   -v "$(pwd)/state:/lab5/state:Z"   -v "$(pwd)/config:/home/node/.openclaw:Z"   -w /workspace   "$IMAGE"

echo "Started $NAME on http://127.0.0.1:18789/"
