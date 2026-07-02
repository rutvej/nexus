from nexus.llm.base import BaseLLM, LLMResponse, NotConfiguredError
import pytest

def test_llm_response_dataclass():
    resp = LLMResponse(
        text="print('hello')",
        model="test-model",
        tokens_used=10,
        latency_ms=150.0,
        success=True
    )
    assert resp.text == "print('hello')"
    assert resp.success is True
    assert resp.error == ""

def test_base_llm_is_abstract():
    with pytest.raises(TypeError):
        BaseLLM()
