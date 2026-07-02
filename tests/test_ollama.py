from unittest.mock import patch, MagicMock
from nexus.llm.ollama_backend import OllamaBackend
import io
import urllib.error

@patch("urllib.request.urlopen")
def test_ollama_is_available_success(mock_urlopen):
    # Mock /api/tags returning model list
    mock_res = MagicMock()
    mock_res.status = 200
    mock_res.read.return_value = b'{"models": [{"name": "qwen2.5-coder:1.5b"}]}'
    mock_urlopen.return_value.__enter__.return_value = mock_res
    
    backend = OllamaBackend(override_model="qwen2.5-coder:1.5b")
    assert backend.is_available() is True

@patch("urllib.request.urlopen")
def test_ollama_is_available_failure(mock_urlopen):
    # Mock timeout / connection error
    mock_urlopen.side_effect = urllib.error.URLError("Connection refused")
    backend = OllamaBackend()
    assert backend.is_available() is False

@patch("urllib.request.urlopen")
def test_ollama_generate_success(mock_urlopen):
    mock_res = MagicMock()
    mock_res.status = 200
    mock_res.read.return_value = b'{"response": "print(\'hello\')", "prompt_eval_count": 10, "eval_count": 5}'
    mock_urlopen.return_value.__enter__.return_value = mock_res
    
    backend = OllamaBackend()
    res = backend.generate("write a python print statement")
    assert res.success is True
    assert res.text == "print('hello')"
    assert res.tokens_used == 15
