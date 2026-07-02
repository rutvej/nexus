from nexus.llm.base import BaseLLM, LLMResponse

class MockLLM(BaseLLM):
    def generate(self, prompt: str, max_tokens: int = 400) -> LLMResponse:
        return LLMResponse(text="Hello", model="mock", tokens_used=1, latency_ms=10.0, success=True)
    def is_available(self) -> bool:
        return True
    def name(self) -> str:
        return "mock"

def test_mock_llm():
    m = MockLLM()
    assert m.name() == "mock"
    assert m.is_available() is True
    res = m.generate("Hi")
    assert res.text == "Hello"
    assert res.success is True
