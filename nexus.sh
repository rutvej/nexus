#!/bin/bash
# nexus.sh - One-command Nexus experiment runner with full automation.
#
# Usage:
#   ./nexus.sh run             - Full clean run (no Docker rebuild)
#   ./nexus.sh run --rebuild   - Clean run + rebuild Docker image first
#   ./nexus.sh resume          - Resume from last incomplete run (skip clean)
#   ./nexus.sh status          - Show current ticket statuses
#   ./nexus.sh pull-model      - Pull the recommended model (qwen2.5-coder:3b)
#   ./nexus.sh logs            - Tail the docker run log
#
# Options (for 'run' and 'resume'):
#   --model MODEL    Use a different model (default: qwen2.5-coder:3b)
#   --goal "..."     Custom goal (default: tweeter Flask app)

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$SCRIPT_DIR/data/last_run.log"

# ─── Defaults ────────────────────────────────────────────────────────────────
MODEL="${NEXUS_MODEL:-qwen2.5-coder:3b}"
OLLAMA_HOST="${OLLAMA_HOST:-http://host.docker.internal:11435}"
GOAL="Create a Python web application called 'tweeter' using Flask. The app needs: 1. User registration (username + password) 2. User login with session management 3. Create a tweet (text only, max 280 chars) 4. View timeline (all tweets, newest first). Use SQLite for the database. Keep it simple."

# ─── Helper: parse extra flags ────────────────────────────────────────────────
CMD="${1:-run}"
shift || true
DO_REBUILD=false
SKIP_CLEAN=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --rebuild)    DO_REBUILD=true; shift ;;
        --model)      MODEL="$2"; shift 2 ;;
        --goal)       GOAL="$2"; shift 2 ;;
        *) shift ;;
    esac
done

# ─── Status display helper ───────────────────────────────────────────────────
show_status() {
    bash "$SCRIPT_DIR/check_tickets.sh"
}

# ─── Run the Docker container ────────────────────────────────────────────────
docker_run() {
    local EXTRA_ARGS="${1:-}"
    mkdir -p "$SCRIPT_DIR/data"
    docker run --rm -u 1000:1000 \
        -v "$SCRIPT_DIR/workspace:/workspace" \
        -v "$SCRIPT_DIR/data:/data" \
        --add-host host.docker.internal:host-gateway \
        -e OLLAMA_HOST="$OLLAMA_HOST" \
        -e NEXUS_DATA_DIR=/data \
        -e NEXUS_WORKSPACE_DIR=/workspace \
        -e OLLAMA_MODEL="$MODEL" \
        nexus-agent:latest \
        "$GOAL" $EXTRA_ARGS 2>&1 | tee "$LOG_FILE"
}

# ─── Commands ────────────────────────────────────────────────────────────────
case "$CMD" in

    run)
        echo ""
        echo "╔══════════════════════════════════════════╗"
        echo "║        Nexus Experiment Runner           ║"
        echo "╚══════════════════════════════════════════╝"
        echo "  Model:  $MODEL"
        echo "  Goal:   ${GOAL:0:60}..."
        echo ""

        if [ "$DO_REBUILD" = true ]; then
            echo "▶ [1/3] Rebuilding Docker image..."
            docker build -t nexus-agent -f "$SCRIPT_DIR/docker/Dockerfile.nexus" "$SCRIPT_DIR" --quiet
            echo "  Done."
            echo ""
        fi

        echo "▶ [$([ "$DO_REBUILD" = true ] && echo "2" || echo "1")/$([ "$DO_REBUILD" = true ] && echo "3" || echo "2")] Cleaning workspace..."
        rm -rf "$SCRIPT_DIR/workspace/src" "$SCRIPT_DIR/workspace/tests"
        rm -f "$SCRIPT_DIR/data/session.db" "$SCRIPT_DIR/data/session.db-shm" "$SCRIPT_DIR/data/session.db-wal"
        echo "  Done."
        echo ""

        echo "▶ Running agent... (logs → data/last_run.log)"
        echo ""
        docker_run

        echo ""
        echo "▶ Results:"
        show_status
        ;;

    resume)
        echo ""
        echo "▶ Resuming last experiment (retrying escalated tickets)..."
        echo "  Model:  $MODEL"
        echo ""
        docker_run "--resume"
        echo ""
        echo "▶ Results:"
        show_status
        ;;

    status)
        show_status
        ;;

    pull-model)
        echo "▶ Pulling recommended model: qwen2.5-coder:3b"
        echo "  Size: ~2GB RAM — good balance of speed and quality on 16GB systems"
        curl -s http://localhost:11435/api/pull -d "{\"name\":\"qwen2.5-coder:3b\"}" | python3 -c "
import sys, json
for line in sys.stdin:
    try:
        d = json.loads(line)
        if 'status' in d:
            print(f\"  {d.get('status','')} {d.get('completed','')}/{d.get('total','')} bytes\" if 'total' in d else f\"  {d['status']}\")
    except: pass
"
        echo "  Done. Run ./nexus.sh run --model qwen2.5-coder:3b"
        ;;

    logs)
        if [ -f "$LOG_FILE" ]; then
            tail -f "$LOG_FILE"
        else
            echo "No log file found at $LOG_FILE. Run an experiment first."
        fi
        ;;

    *)
        echo "Unknown command: $CMD"
        echo "Usage: ./nexus.sh [run|resume|status|pull-model|logs] [--rebuild] [--model MODEL] [--goal '...']"
        exit 1
        ;;

esac
