import json
import urllib.request
import urllib.error
import time
from typing import Optional
from nexus import config
from nexus.llm.base import BaseLLM, LLMResponse

class OllamaLLM(BaseLLM):
    def __init__(self, model_name: str = None, host_url: str = None, keep_alive: str = "5m"):
        self.model_name = model_name or config.MODEL_NAME
        self.host_url = host_url or config.OLLAMA_HOST
        self.keep_alive = keep_alive

    def name(self) -> str:
        return self.model_name

    def is_available(self) -> bool:
        try:
            url = f"{self.host_url}/api/tags"
            # Short timeout to avoid blocking startup if Ollama is down
            with urllib.request.urlopen(url, timeout=3) as r:
                return r.status == 200
        except Exception:
            return False

    def generate(self, prompt: str, max_tokens: int = 400) -> LLMResponse:
        url = f"{self.host_url}/api/generate"
        data = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "keep_alive": self.keep_alive,
            "options": {
                "temperature": 0.0,  # 0.0 for deterministic code generation
                "num_predict": max_tokens,
                "seed": 42
            }
        }

        headers = {"Content-Type": "application/json"}
        req_body = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(url, data=req_body, headers=headers, method="POST")

        start_time = time.time()
        try:
            # timeout matches config.TIMEOUT_OLLAMA
            with urllib.request.urlopen(req, timeout=config.TIMEOUT_OLLAMA) as response:
                resp_body = response.read().decode("utf-8")
                latency_ms = (time.time() - start_time) * 1000
                resp_data = json.loads(resp_body)
                
                text = resp_data.get("response", "")
                tokens = resp_data.get("eval_count", 0) + resp_data.get("prompt_eval_count", 0)
                
                return LLMResponse(
                    text=text,
                    model=self.model_name,
                    tokens_used=tokens,
                    latency_ms=latency_ms,
                    success=True
                )
        except urllib.error.URLError as e:
            latency_ms = (time.time() - start_time) * 1000
            return LLMResponse(
                text="",
                model=self.model_name,
                tokens_used=0,
                latency_ms=latency_ms,
                success=False,
                error=f"HTTP request failed: {e}"
            )
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            return LLMResponse(
                text="",
                model=self.model_name,
                tokens_used=0,
                latency_ms=latency_ms,
                success=False,
                error=f"Unexpected error: {e}"
            )
