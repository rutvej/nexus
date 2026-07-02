from nexus import config
from nexus.llm.base import BaseLLM, LLMResponse

class DeepSeekBackend(BaseLLM):
    def name(self) -> str:
        return "deepseek/deepseek-chat"

    def is_available(self) -> bool:
        return bool(config.DEEPSEEK_API_KEY)

    def generate(self, prompt: str, max_tokens: int = 400) -> LLMResponse:
        if not self.is_available():
            return LLMResponse(
                text="",
                model="deepseek-chat",
                tokens_used=0,
                latency_ms=0,
                success=False,
                error="DeepSeek API key not configured."
            )
        # Placeholder for actual request
        raise NotImplementedError("Cloud API integration pending real HTTP call implementation")
