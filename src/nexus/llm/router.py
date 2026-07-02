from typing import List, Optional
from nexus.llm.base import BaseLLM, LLMResponse, NotConfiguredError
from nexus.tickets.models import Ticket

class ModelRouter:
    def __init__(self, local_llm: BaseLLM, cloud_llms: List[BaseLLM] = None):
        self.local_llm = local_llm
        self.cloud_llms = cloud_llms or []

    def route_and_generate(self, prompt: str, ticket: Ticket, max_tokens: int = 400) -> LLMResponse:
        """
        Routes the prompt to the appropriate model based on ticket retry status.
        If retry_count < 3: use local model.
        If retry_count >= 3: use the first available cloud model.
        If both fail or are unavailable, return an unsuccessful response.
        """
        # Local routing
        if ticket.retry_count < 3:
            if self.local_llm.is_available():
                return self.local_llm.generate(prompt, max_tokens)
            else:
                return LLMResponse(
                    text="",
                    model="local",
                    tokens_used=0,
                    latency_ms=0.0,
                    success=False,
                    error="Local model is not available."
                )

        # Cloud routing (retry_count >= 3)
        available_cloud = [c for c in self.cloud_llms if c.is_available()]
        if available_cloud:
            cloud_llm = available_cloud[0]
            try:
                return cloud_llm.generate(prompt, max_tokens)
            except NotConfiguredError as e:
                return LLMResponse(
                    text="",
                    model=cloud_llm.name(),
                    tokens_used=0,
                    latency_ms=0.0,
                    success=False,
                    error=f"Cloud model configuration error: {e}"
                )
            except Exception as e:
                return LLMResponse(
                    text="",
                    model=cloud_llm.name(),
                    tokens_used=0,
                    latency_ms=0.0,
                    success=False,
                    error=f"Cloud model generation failed: {e}"
                )

        return LLMResponse(
            text="",
            model="router",
            tokens_used=0,
            latency_ms=0.0,
            success=False,
            error="Local model exceeded retries and no cloud model is configured/available."
        )
