import sqlite3
import os
from typing import Dict, Any, Tuple, Optional
from nexus.models.backends.ollama import OllamaBackend, DEFAULT_OLLAMA_URL, CUSTOM_OLLAMA_URL

# Default fallback profiles if DB scores are empty/missing
DEFAULT_PROFILES = {
    "qwen2.5:1.5b": {
        "host": CUSTOM_OLLAMA_URL,
        "scores": {
            "code_generation": 0.85,
            "debugging": 0.80,
            "planning": 0.75,
            "tool_calling": 0.85,
            "json_generation": 0.85,
            "reasoning": 0.10
        }
    },
    "qwen2.5-coder:1.5b": {
        "host": DEFAULT_OLLAMA_URL,
        "scores": {
            "code_generation": 0.90,
            "debugging": 0.85,
            "planning": 0.75,
            "tool_calling": 0.85,
            "json_generation": 0.85,
            "reasoning": 0.10
        }
    },
    "gemma2:2b": {
        "host": DEFAULT_OLLAMA_URL,
        "scores": {
            "code_generation": 0.75,
            "debugging": 0.70,
            "planning": 0.75,
            "tool_calling": 0.75,
            "json_generation": 0.75,
            "reasoning": 0.20
        }
    },
    "qwen3.5:2b": {
        "host": DEFAULT_OLLAMA_URL,
        "scores": {
            "code_generation": 0.30,
            "debugging": 0.30,
            "planning": 0.40,
            "tool_calling": 0.70,
            "json_generation": 0.70,
            "reasoning": 0.60
        }
    }
}

class ModelRouter:
    def __init__(self, db_path: str = "/home/rutvej/nexus_eval/nexus_eval.db"):
        self.db_path = db_path
        self.backends = {
            DEFAULT_OLLAMA_URL: OllamaBackend(DEFAULT_OLLAMA_URL),
            CUSTOM_OLLAMA_URL: OllamaBackend(CUSTOM_OLLAMA_URL)
        }
        self.scores = {}
        self.load_scores()

    def load_scores(self):
        # Initialize scores with default profiles
        for model, profile in DEFAULT_PROFILES.items():
            self.scores[model] = {
                "host": profile["host"],
                "scores": profile["scores"].copy()
            }

        # Override with database scores if available
        if os.path.exists(self.db_path):
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT model_name, task_type, score FROM model_scores")
                rows = cursor.fetchall()
                conn.close()

                for model_name, task_type, score in rows:
                    category = task_type
                    if model_name not in self.scores:
                        self.scores[model_name] = {
                            "host": DEFAULT_OLLAMA_URL,
                            "scores": {}
                        }
                    self.scores[model_name]["scores"][category] = score
            except Exception as e:
                print(f"Warning: Failed to load scores from database: {e}")

    def route(self, task_type: str) -> Tuple[str, str]:
        """
        Route a task type to the best available model.
        Returns (model_name, host_url).
        """
        best_model = None
        best_score = -1.0
        best_host = DEFAULT_OLLAMA_URL

        # Find the model with the highest score for this task type that is available
        for model_name, profile in self.scores.items():
            score = profile["scores"].get(task_type, 0.0)
            host = profile["host"]
            
            # Check if this model is available
            backend = self.backends.get(host)
            if backend and backend.is_available():
                if score > best_score:
                    best_score = score
                    best_model = model_name
                    best_host = host

        if not best_model:
            # Absolute fallback if no model is running/available
            raise RuntimeError("No Ollama models are currently available. Please check that Ollama is running.")

        return best_model, best_host

    def generate(self, task_type: str, prompt: str, system_prompt: Optional[str] = None, json_mode: bool = False) -> Dict[str, Any]:
        """Route the task and generate the response."""
        model_name, host_url = self.route(task_type)
        backend = self.backends[host_url]
        
        # Log routing decision
        # print(f"[Router] Routing task '{task_type}' to '{model_name}' on {host_url}")
        
        return backend.generate(model_name, prompt, system_prompt, json_mode)
