#!/usr/bin/env bash
# Startup script for the inference service.
# Loaded automatically when the container starts.
set -e

echo "[startup] Starting inference service..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level info