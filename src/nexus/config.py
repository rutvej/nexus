import os
from pathlib import Path

# Base Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
DATA_DIR = Path(os.getenv("NEXUS_DATA_DIR", PROJECT_ROOT / ".nexus"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "session.db"
WORKSPACE_DIR = Path(os.getenv("NEXUS_WORKSPACE_DIR", PROJECT_ROOT / "workspace"))
WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)

# LLM Configuration
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11435")
MODEL_NAME = os.getenv("MODEL_NAME", "qwen2.5-coder:1.5b")

# Limits & Thresholds
MAX_RETRIES_PER_TICKET = 3
MAX_CONSECUTIVE_FAILURES = 5
TIMEOUT_OLLAMA = 30
TIMEOUT_TESTS = 60

# Cloud API Keys (for stubs)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
