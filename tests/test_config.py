import os
from pathlib import Path
from nexus import config

def test_config_paths():
    assert isinstance(config.PROJECT_ROOT, Path)
    assert isinstance(config.DATA_DIR, Path)
    assert isinstance(config.DB_PATH, Path)
    assert isinstance(config.WORKSPACE_DIR, Path)

def test_config_defaults():
    assert config.MAX_RETRIES_PER_TICKET == 3
    assert config.MAX_CONSECUTIVE_FAILURES == 5
    assert config.TIMEOUT_OLLAMA == 180
    assert config.TIMEOUT_TESTS == 60
