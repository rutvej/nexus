#!/bin/bash
# run_fast.sh - Fast experiment runner (no Docker rebuild, runs directly on host).
#
# SPEEDUPS vs run_experiment.sh:
#   - Skips docker build (~30s saved per run)
#   - Runs agent in host venv (no container overhead)
#   - Uses a configurable model and Ollama host
#   - Supports --skip-clean to resume a failed experiment mid-run
#   - Supports --no-tests to skip pytest verification (faster, but less rigorous)
#
# USAGE:
#   ./run_fast.sh                          # full clean run with defaults
#   ./run_fast.sh --skip-clean             # resume experiment without wiping workspace
#   ./run_fast.sh --no-tests               # skip pytest check (fastest, for debugging LLM output only)
#   ./run_fast.sh --model qwen2.5-coder:7b # use a different/larger model
#   ./run_fast.sh "your custom goal here"  # run with a custom goal

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="$SCRIPT_DIR/venv/bin/python"

# Defaults
SKIP_CLEAN=false
NO_TESTS=false
MODEL="qwen2.5-coder:1.5b"
OLLAMA_HOST="http://localhost:11435"
GOAL="Create a Python web application called 'tweeter' using Flask. The app needs: 1. User registration (username + password) 2. User login with session management 3. Create a tweet (text only, max 280 chars) 4. View timeline (all tweets, newest first). Use SQLite for the database. Keep it simple."

# Parse args
while [[ $# -gt 0 ]]; do
    case "$1" in
        --skip-clean) SKIP_CLEAN=true; shift ;;
        --no-tests)   NO_TESTS=true; shift ;;
        --model)      MODEL="$2"; shift 2 ;;
        --host)       OLLAMA_HOST="$2"; shift 2 ;;
        *) GOAL="$1"; shift ;;
    esac
done

echo "=== Nexus Fast Experiment Runner ==="
echo "  Model:       $MODEL"
echo "  Ollama Host: $OLLAMA_HOST"
echo "  Skip Clean:  $SKIP_CLEAN"
echo "  No Tests:    $NO_TESTS"
echo ""

# Step 1: Clean up
if [ "$SKIP_CLEAN" = false ]; then
    echo "=== [1/2] Cleaning up previous experiment artifacts ==="
    rm -rf "$SCRIPT_DIR/workspace/src" "$SCRIPT_DIR/workspace/tests"
    rm -f "$SCRIPT_DIR/data/session.db" "$SCRIPT_DIR/data/session.db-shm" "$SCRIPT_DIR/data/session.db-wal"
    echo "Done."
    echo ""
else
    echo "=== [1/2] Skipping cleanup (--skip-clean) ==="
    echo ""
fi

# Step 2: Run agent on host venv directly
echo "=== [2/2] Running Nexus Agent (host venv) ==="
echo "Goal: $GOAL"
echo ""

NEXUS_DATA_DIR="$SCRIPT_DIR/data" \
NEXUS_WORKSPACE_DIR="$SCRIPT_DIR/workspace" \
OLLAMA_HOST="$OLLAMA_HOST" \
OLLAMA_MODEL="$MODEL" \
NEXUS_NO_TESTS="${NO_TESTS}" \
"$VENV_PYTHON" -m nexus "$GOAL"

echo ""
echo "=== Experiment complete. Run ./check_tickets.sh to inspect results. ==="
