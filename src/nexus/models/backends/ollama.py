import json
import urllib.request
import urllib.error
import time
from typing import Dict, Any, Optional

DEFAULT_OLLAMA_URL = "http://localhost:11434"
CUSTOM_OLLAMA_URL = "http://localhost:11435"

class OllamaBackend:
    def __init__(self, host_url: str = DEFAULT_OLLAMA_URL):
        self.host_url = host_url

    def is_available(self) -> bool:
        try:
            with urllib.request.urlopen(f"{self.host_url}/api/tags", timeout=3) as r:
                return r.status == 200
        except Exception:
            return False

    def generate(self, model: str, prompt: str, system_prompt: Optional[str] = None, json_mode: bool = False) -> Dict[str, Any]:
        url = f"{self.host_url}/api/generate"
        data = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "seed": 42
            }
        }
        if system_prompt:
            data["system"] = system_prompt
        if json_mode:
            data["format"] = "json"

        headers = {"Content-Type": "application/json"}
        req_body = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(url, data=req_body, headers=headers, method="POST")

        start_time = time.time()
        try:
            # We use a long timeout (300s) because CPU generation can be slow
            with urllib.request.urlopen(req, timeout=300) as response:
                resp_body = response.read().decode("utf-8")
                duration_ms = (time.time() - start_time) * 1000
                resp_data = json.loads(resp_body)
                
                return {
                    "text": resp_data.get("response", ""),
                    "tokens_prompt": resp_data.get("prompt_eval_count", 0),
                    "tokens_generated": resp_data.get("eval_count", 0),
                    "latency_ms": duration_ms
                }
        except urllib.error.URLError as e:
            raise RuntimeError(f"Ollama call failed on {url} for model {model}: {e}")
