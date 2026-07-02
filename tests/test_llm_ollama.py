from unittest.mock import patch, MagicMock
import urllib.error
from io import BytesIO
from nexus.llm.ollama_backend import OllamaLLM

def test_ollama_name():
    llm = OllamaLLM(model_name="test-coder:1.5b")
    assert llm.name() == "test-coder:1.5b"

@patch("urllib.request.urlopen")
def test_ollama_is_available_success(mock_urlopen):
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_urlopen.return_value.__enter__.return_value = mock_resp

    llm = OllamaLLM(host_url="http://fake-host:11435")
    assert llm.is_available() is True

@patch("urllib.request.urlopen")
def test_ollama_is_available_failure(mock_urlopen):
    mock_urlopen.side_effect = urllib.error.URLError("Connection refused")

    llm = OllamaLLM(host_url="http://fake-host:11435")
    assert llm.is_available() is False

@patch("urllib.request.urlopen")
def test_ollama_generate_success(mock_urlopen):
    mock_resp = MagicMock()
    mock_resp.read.return_value = b'{"response": "def add(a, b): return a + b", "eval_count": 10, "prompt_eval_count": 5}'
    mock_urlopen.return_value.__enter__.return_value = mock_resp

    llm = OllamaLLM(model_name="test-coder:1.5b", host_url="http://fake-host:11435")
    resp = llm.generate("Write an add function")
    
    assert resp.success is True
    assert resp.text == "def add(a, b): return a + b"
    assert resp.tokens_used == 15
    assert resp.model == "test-coder:1.5b"

@patch("urllib.request.urlopen")
def test_ollama_generate_failure(mock_urlopen):
    mock_urlopen.side_effect = urllib.error.URLError("Timeout")

    llm = OllamaLLM(model_name="test-coder:1.5b", host_url="http://fake-host:11435")
    resp = llm.generate("Write an add function")
    
    assert resp.success is False
    assert resp.text == ""
    assert "HTTP request failed" in resp.error
