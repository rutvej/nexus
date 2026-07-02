from typing import List
from nexus.llm.base import BaseLLM, LLMResponse
from nexus.llm.ollama_backend import OllamaBackend
from nexus.llm.cloud.openai_backend import OpenAIBackend
from nexus.llm.cloud.anthropic_backend import AnthropicBackend
from nexus.llm.cloud.google_backend import GoogleBackend
from nexus.llm.cloud.deepseek_backend import DeepSeekBackend

class ModelRouter:
    def __init__(self, local_override: BaseLLM = None, cloud_overrides: List[BaseLLM] = None):
        self.local = local_override or OllamaBackend()
        self.cloud_backends = cloud_overrides or [
            OpenAIBackend(),
            AnthropicBackend(),
            GoogleBackend(),
            DeepSeekBackend()
        ]

    def route_and_generate(self, prompt: str, ticket=None, max_tokens: int = 400) -> LLMResponse:
        """
        Coordinates routing: tries local first, then falls back to first available cloud provider.
        """
        # 1. Try local model
        if self.local.is_available():
            res = self.local.generate(prompt, max_tokens)
            if res.success:
                return res
        
        # 2. Try cloud backends (first available)
        for backend in self.cloud_backends:
            if backend.is_available():
                res = backend.generate(prompt, max_tokens)
                if res.success:
                    return res
        
        # 3. No backends available
        return LLMResponse(
            text="",
            model="none",
            tokens_used=0,
            latency_ms=0.0,
            success=False,
            error="No available LLM backends."
        )
