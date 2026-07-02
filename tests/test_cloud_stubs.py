from nexus.llm.cloud.openai_backend import OpenAIBackend
from nexus.llm.cloud.anthropic_backend import AnthropicBackend
from nexus.llm.cloud.google_backend import GoogleBackend
from nexus.llm.cloud.deepseek_backend import DeepSeekBackend
from nexus import config

def test_stubs_not_available_by_default():
    # Make sure keys are empty in test run context
    config.OPENAI_API_KEY = ""
    config.ANTHROPIC_API_KEY = ""
    config.GOOGLE_API_KEY = ""
    config.DEEPSEEK_API_KEY = ""

    openai = OpenAIBackend()
    assert openai.is_available() is False
    res = openai.generate("Hi")
    assert res.success is False
    assert "not configured" in res.error

    anthropic = AnthropicBackend()
    assert anthropic.is_available() is False
    res = anthropic.generate("Hi")
    assert res.success is False

    google = GoogleBackend()
    assert google.is_available() is False
    res = google.generate("Hi")
    assert res.success is False

    deepseek = DeepSeekBackend()
    assert deepseek.is_available() is False
    res = deepseek.generate("Hi")
    assert res.success is False
