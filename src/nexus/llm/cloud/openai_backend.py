from nexus import config
from nexus.llm.base import BaseLLM, LLMResponse

class OpenAIBackend(BaseLLM):
    def name(self) -> str:
        return "openai/gpt-4o-mini"

    def is_available(self) -> bool:
        return bool(config.OPENAI_API_KEY)

    def generate(self, prompt: str, max_tokens: int = 400) -> LLMResponse:
        if not self.is_available():
            return LLMResponse(
                text="",
                model="gpt-4o-mini",
                tokens_used=0,
                latency_ms=0,
                success=False,
                error="OpenAI API key not configured."
            )
        # Placeholder for actual request
        return LLMResponse(
            text="Stub Response",
            model="gpt-4o-mini",
            tokens_used=10,
            latency_ms=100.0,
            success=True
        )
