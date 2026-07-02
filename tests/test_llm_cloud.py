import pytest
from nexus.llm.base import NotConfiguredError
from nexus.llm.cloud_stub import OpenAILLM, AnthropicLLM, GoogleLLM, DeepSeekLLM
from nexus import config

def test_cloud_stubs_not_configured():
    # Temporarily clear keys to ensure they are missing
    config.OPENAI_API_KEY = ""
    config.ANTHROPIC_API_KEY = ""
    config.GOOGLE_API_KEY = ""
    config.DEEPSEEK_API_KEY = ""

    for llm_class in [OpenAILLM, AnthropicLLM, GoogleLLM, DeepSeekLLM]:
        llm = llm_class()
        assert llm.is_available() is False
        with pytest.raises(NotConfiguredError):
            llm.generate("test")

def test_cloud_stubs_configured():
    config.OPENAI_API_KEY = "dummy-key"
    llm = OpenAILLM()
    assert llm.is_available() is True
    resp = llm.generate("test")
    assert resp.success is True
    assert "OpenAI Stub" in resp.text
