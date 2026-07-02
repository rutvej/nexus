from nexus import config
from nexus.llm.base import BaseLLM, LLMResponse, NotConfiguredError

class OpenAILLM(BaseLLM):
    def __init__(self, model_name: str = "gpt-4o-mini"):
        self.model_name = model_name
        self.api_key = config.OPENAI_API_KEY

    def name(self) -> str:
        return f"openai/{self.model_name}"

    def is_available(self) -> bool:
        return bool(self.api_key)

    def generate(self, prompt: str, max_tokens: int = 400) -> LLMResponse:
        if not self.is_available():
            raise NotConfiguredError("OpenAI API key is not configured.")
        # Stub response if configured
        return LLMResponse(
            text=f"# OpenAI Stub Output for model {self.model_name}\npass",
            model=self.name(),
            tokens_used=10,
            latency_ms=100.0,
            success=True
        )

class AnthropicLLM(BaseLLM):
    def __init__(self, model_name: str = "claude-3-5-sonnet-20241022"):
        self.model_name = model_name
        self.api_key = config.ANTHROPIC_API_KEY

    def name(self) -> str:
        return f"anthropic/{self.model_name}"

    def is_available(self) -> bool:
        return bool(self.api_key)

    def generate(self, prompt: str, max_tokens: int = 400) -> LLMResponse:
        if not self.is_available():
            raise NotConfiguredError("Anthropic API key is not configured.")
        # Stub response if configured
        return LLMResponse(
            text=f"# Anthropic Stub Output for model {self.model_name}\npass",
            model=self.name(),
            tokens_used=10,
            latency_ms=100.0,
            success=True
        )

class GoogleLLM(BaseLLM):
    def __init__(self, model_name: str = "gemini-1.5-flash"):
        self.model_name = model_name
        self.api_key = config.GOOGLE_API_KEY

    def name(self) -> str:
        return f"google/{self.model_name}"

    def is_available(self) -> bool:
        return bool(self.api_key)

    def generate(self, prompt: str, max_tokens: int = 400) -> LLMResponse:
        if not self.is_available():
            raise NotConfiguredError("Google API key is not configured.")
        # Stub response if configured
        return LLMResponse(
            text=f"# Google Stub Output for model {self.model_name}\npass",
            model=self.name(),
            tokens_used=10,
            latency_ms=100.0,
            success=True
        )

class DeepSeekLLM(BaseLLM):
    def __init__(self, model_name: str = "deepseek-coder"):
        self.model_name = model_name
        self.api_key = config.DEEPSEEK_API_KEY

    def name(self) -> str:
        return f"deepseek/{self.model_name}"

    def is_available(self) -> bool:
        return bool(self.api_key)

    def generate(self, prompt: str, max_tokens: int = 400) -> LLMResponse:
        if not self.is_available():
            raise NotConfiguredError("DeepSeek API key is not configured.")
        # Stub response if configured
        return LLMResponse(
            text=f"# DeepSeek Stub Output for model {self.model_name}\npass",
            model=self.name(),
            tokens_used=10,
            latency_ms=100.0,
            success=True
        )
