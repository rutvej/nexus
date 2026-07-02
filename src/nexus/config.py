import os
from pathlib import Path

# Paths
PROJECT_ROOT = Path(os.environ.get("NEXUS_PROJECT_ROOT", os.getcwd()))
DATA_DIR = Path(os.environ.get("NEXUS_DATA_DIR", PROJECT_ROOT / "data"))
WORKSPACE_DIR = Path(os.environ.get("NEXUS_WORKSPACE_DIR", PROJECT_ROOT / "workspace"))
DB_PATH = DATA_DIR / "session.db"

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)

# Limits & Thresholds
MAX_RETRIES_PER_TICKET = 3
MAX_CONSECUTIVE_FAILURES = 5
TIMEOUT_OLLAMA = 180
TIMEOUT_TESTS = 60

# Model config
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5-coder:1.5b")

# Cloud API keys (stubs check presence)
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
