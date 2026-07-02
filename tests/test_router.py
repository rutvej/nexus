from nexus.llm.base import BaseLLM, LLMResponse
from nexus.llm.router import ModelRouter

class FakeLLM(BaseLLM):
    def __init__(self, name_val: str, available: bool, should_succeed: bool, response_text: str = ""):
        self.name_val = name_val
        self.available = available
        self.should_succeed = should_succeed
        self.response_text = response_text

    def name(self) -> str:
        return self.name_val
    def is_available(self) -> bool:
        return self.available
    def generate(self, prompt: str, max_tokens: int = 400) -> LLMResponse:
        if not self.should_succeed:
            return LLMResponse(text="", model=self.name_val, tokens_used=0, latency_ms=1.0, success=False, error="Fail")
        return LLMResponse(text=self.response_text, model=self.name_val, tokens_used=5, latency_ms=10.0, success=True)

def test_router_local_success():
    local = FakeLLM("local", available=True, should_succeed=True, response_text="local_out")
    router = ModelRouter(local_override=local)
    res = router.route_and_generate("prompt")
    assert res.success is True
    assert res.text == "local_out"
    assert res.model == "local"

def test_router_local_fails_cloud_success():
    local = FakeLLM("local", available=True, should_succeed=False)
    cloud1 = FakeLLM("cloud1", available=True, should_succeed=True, response_text="cloud1_out")
    router = ModelRouter(local_override=local, cloud_overrides=[cloud1])
    res = router.route_and_generate("prompt")
    assert res.success is True
    assert res.text == "cloud1_out"
    assert res.model == "cloud1"

def test_router_all_fail():
    local = FakeLLM("local", available=False, should_succeed=False)
    cloud1 = FakeLLM("cloud1", available=False, should_succeed=False)
    router = ModelRouter(local_override=local, cloud_overrides=[cloud1])
    res = router.route_and_generate("prompt")
    assert res.success is False
    assert "No available" in res.error
