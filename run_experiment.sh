#!/bin/bash
# run_experiment.sh - Automates the full Nexus experiment cycle:
# 1. Cleans workspace and session DB
# 2. Rebuilds the Docker image
# 3. Runs the containerized agent

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Default goal prompt
GOAL="${1:-Create a Python web application called 'tweeter' using Flask. The app needs: 1. User registration (username + password) 2. User login with session management 3. Create a tweet (text only, max 280 chars) 4. View timeline (all tweets, newest first). Use SQLite for the database. Keep it simple.}"

echo "=== [1/3] Cleaning up previous experiment artifacts ==="
rm -rf "$SCRIPT_DIR/workspace/src" "$SCRIPT_DIR/workspace/tests"
rm -f "$SCRIPT_DIR/data/session.db" "$SCRIPT_DIR/data/session.db-shm" "$SCRIPT_DIR/data/session.db-wal"
echo "Done."

echo ""
echo "=== [2/3] Rebuilding Docker Image ==="
docker build -t nexus-agent -f "$SCRIPT_DIR/docker/Dockerfile.nexus" "$SCRIPT_DIR"

echo ""
echo "=== [3/3] Running Containerized Agent ==="
echo "Model: ${OLLAMA_MODEL:-qwen2.5-coder:3b}"
echo "Goal: $GOAL"
echo ""
docker run --rm -u 1000:1000 \
  -v "$SCRIPT_DIR/workspace:/workspace" \
  -v "$SCRIPT_DIR/data:/data" \
  --add-host host.docker.internal:host-gateway \
  -e OLLAMA_HOST=http://host.docker.internal:11435 \
  -e OLLAMA_MODEL="${OLLAMA_MODEL:-qwen2.5-coder:3b}" \
  -e NEXUS_DATA_DIR=/data \
  -e NEXUS_WORKSPACE_DIR=/workspace \
  nexus-agent:latest \
  "$GOAL"

echo ""
echo "=== Experiment complete. Run ./check_tickets.sh to inspect results. ==="
