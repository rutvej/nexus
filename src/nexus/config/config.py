import os
import sys

# In Python 3.11+, tomllib is in the standard library.
if sys.version_info >= (3, 11):
    import tomllib
else:
    # Fallback if needed, though we checked the system has 3.12.3
    import tomllib

DEFAULT_CONFIG = """
[agent]
max_steps = 15
permission_profile = "balanced" # conservative, balanced, permissive

[permissions]
allowed_paths = ["."]
denied_paths = [".git", ".env"]

[routing]
database_path = "/home/rutvej/nexus_eval/nexus_eval.db"
"""

from typing import Any

class Config:
    def __init__(self, config_path: str = None):
        self.config_path = config_path or os.path.join(os.getcwd(), ".nexus_config.toml")
        self.data = {}
        self.load()

    def load(self):
        if os.path.exists(self.config_path):
            with open(self.config_path, "rb") as f:
                self.data = tomllib.load(f)
        else:
            # Parse default config
            self.data = tomllib.loads(DEFAULT_CONFIG)

    def get(self, key_path: str, default: Any = None) -> Any:
        parts = key_path.split(".")
        val = self.data
        for p in parts:
            if isinstance(val, dict) and p in val:
                val = val[p]
            else:
                return default
        return val
