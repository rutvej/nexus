import urllib.request
import urllib.error
import json
import time
from nexus import config
from nexus.llm.base import BaseLLM, LLMResponse

class OllamaBackend(BaseLLM):
    def __init__(self, override_host: str = None, override_model: str = None):
        self.host = override_host or config.OLLAMA_HOST
        self.model = override_model or config.OLLAMA_MODEL

    def name(self) -> str:
        return f"ollama/{self.model}"

    def is_available(self) -> bool:
        url = f"{self.host.rstrip('/')}/api/tags"
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))
                    models = [m["name"] for m in data.get("models", [])]
                    # Check if our target model or base of it exists
                    return any(self.model in m or m in self.model for m in models)
        except Exception:
            return False
        return False

    def generate(self, prompt: str, max_tokens: int = 400) -> LLMResponse:
        url = f"{self.host.rstrip('/')}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": 0.0  # Greedy decoding for deterministic code output
            },
            "keep_alive": "5m"  # Pin model in memory for 5 minutes
        }
        
        start_time = time.time()
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=config.TIMEOUT_OLLAMA) as response:
                latency = (time.time() - start_time) * 1000
                if response.status == 200:
                    res_data = json.loads(response.read().decode("utf-8"))
                    text = res_data.get("response", "").strip()
                    # Qwen returns token counts in response fields
                    prompt_eval_count = res_data.get("prompt_eval_count", 0)
                    eval_count = res_data.get("eval_count", 0)
                    tokens = prompt_eval_count + eval_count
                    return LLMResponse(
                        text=text,
                        model=self.model,
                        tokens_used=tokens,
                        latency_ms=latency,
                        success=True
                    )
                else:
                    return LLMResponse(
                        text="",
                        model=self.model,
                        tokens_used=0,
                        latency_ms=latency,
                        success=False,
                        error=f"HTTP Error {response.status}"
                    )
        except Exception as e:
            latency = (time.time() - start_time) * 1000
            return LLMResponse(
                text="",
                model=self.model,
                tokens_used=0,
                latency_ms=latency,
                success=False,
                error=str(e)
            )
