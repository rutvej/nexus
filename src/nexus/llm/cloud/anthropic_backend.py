from nexus import config
from nexus.llm.base import BaseLLM, LLMResponse

class AnthropicBackend(BaseLLM):
    def name(self) -> str:
        return "anthropic/claude-3-haiku"

    def is_available(self) -> bool:
        return bool(config.ANTHROPIC_API_KEY)

    def generate(self, prompt: str, max_tokens: int = 400) -> LLMResponse:
        if not self.is_available():
            return LLMResponse(
                text="",
                model="claude-3-haiku",
                tokens_used=0,
                latency_ms=0,
                success=False,
                error="Anthropic API key not configured."
            )
        # Placeholder for actual request
        return LLMResponse(
            text="Stub Response",
            model="claude-3-haiku",
            tokens_used=10,
            latency_ms=100.0,
            success=True
        )
