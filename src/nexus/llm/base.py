from abc import ABC, abstractmethod
from dataclasses import dataclass

class NotConfiguredError(Exception):
    """Exception raised when an LLM provider is not configured."""
    pass

@dataclass
class LLMResponse:
    text: str
    model: str
    tokens_used: int
    latency_ms: float
    success: bool
    error: str = ""

class BaseLLM(ABC):
    @abstractmethod
    def generate(self, prompt: str, max_tokens: int = 400) -> LLMResponse:
        """Generates text from the LLM for a given prompt."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Returns True if the backend is configured and responsive."""
        pass
    
    @abstractmethod
    def name(self) -> str:
        """Returns the identifier name of the LLM model/backend."""
        pass
