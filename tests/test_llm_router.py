from unittest.mock import MagicMock
from nexus.llm.base import BaseLLM, LLMResponse
from nexus.llm.router import ModelRouter
from nexus.tickets.models import Ticket, TicketType

def test_router_local_under_3_retries():
    local_mock = MagicMock(spec=BaseLLM)
    local_mock.is_available.return_value = True
    local_mock.generate.return_value = LLMResponse(
        text="local code", model="local-model", tokens_used=10, latency_ms=10.0, success=True
    )
    
    cloud_mock = MagicMock(spec=BaseLLM)
    
    router = ModelRouter(local_llm=local_mock, cloud_llms=[cloud_mock])
    ticket = Ticket(id="T1", type=TicketType.WRITE_FUNCTION, title="test", retry_count=2)
    
    resp = router.route_and_generate("prompt", ticket)
    assert resp.success is True
    assert resp.text == "local code"
    local_mock.generate.assert_called_once()
    cloud_mock.generate.assert_not_called()

def test_router_cloud_fallback():
    local_mock = MagicMock(spec=BaseLLM)
    
    cloud_mock = MagicMock(spec=BaseLLM)
    cloud_mock.is_available.return_value = True
    cloud_mock.name.return_value = "cloud-model"
    cloud_mock.generate.return_value = LLMResponse(
        text="cloud code", model="cloud-model", tokens_used=20, latency_ms=50.0, success=True
    )
    
    router = ModelRouter(local_llm=local_mock, cloud_llms=[cloud_mock])
    ticket = Ticket(id="T1", type=TicketType.WRITE_FUNCTION, title="test", retry_count=3)
    
    resp = router.route_and_generate("prompt", ticket)
    assert resp.success is True
    assert resp.text == "cloud code"
    local_mock.generate.assert_not_called()
    cloud_mock.generate.assert_called_once()

def test_router_escalation_no_cloud():
    local_mock = MagicMock(spec=BaseLLM)
    
    router = ModelRouter(local_llm=local_mock, cloud_llms=[])
    ticket = Ticket(id="T1", type=TicketType.WRITE_FUNCTION, title="test", retry_count=3)
    
    resp = router.route_and_generate("prompt", ticket)
    assert resp.success is False
    assert "no cloud model is configured" in resp.error
