# tests/test_llm_client.py
"""
llm_client.py builds a real genai.Client() at import time (module-level
code), so rather than mocking the import machinery we patch the already-
constructed `client` object's `.models.generate_content` method. This
keeps the test fast, offline, and free — no real Gemini calls or API key
needed.
"""
from unittest.mock import MagicMock, patch

from analysis import llm_client


def test_ask_gemini_returns_response_text():
    fake_response = MagicMock()
    fake_response.text = "Hello from Gemini"

    with patch.object(llm_client.client.models, "generate_content",
                       return_value=fake_response) as mock_generate:
        result = llm_client.ask_gemini("say hi")

    assert result == "Hello from Gemini"
    mock_generate.assert_called_once()


def test_ask_gemini_passes_prompt_as_contents():
    fake_response = MagicMock()
    fake_response.text = "ok"

    with patch.object(llm_client.client.models, "generate_content",
                       return_value=fake_response) as mock_generate:
        llm_client.ask_gemini("what is 2+2?")

    _, kwargs = mock_generate.call_args
    assert kwargs["contents"] == "what is 2+2?"


def test_ask_gemini_uses_expected_model():
    fake_response = MagicMock()
    fake_response.text = "ok"

    with patch.object(llm_client.client.models, "generate_content",
                       return_value=fake_response) as mock_generate:
        llm_client.ask_gemini("prompt")

    _, kwargs = mock_generate.call_args
    assert kwargs["model"] == "gemini-2.5-flash"
