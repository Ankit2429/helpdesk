"""Tests for the Ollama language model adapter."""

from types import SimpleNamespace

from campus_helpdesk.infrastructure.llm.ollama_service import OllamaLLMService


class FakeOllamaClient:
    """Captures the chat call without connecting to Ollama."""

    def __init__(self) -> None:
        self.request: dict[str, object] | None = None

    def chat(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        options: dict[str, float | int],
        stream: bool,
    ) -> object:
        self.request = {"model": model, "messages": messages, "options": options, "stream": stream}
        return SimpleNamespace(message=SimpleNamespace(content="  The library is in Block A.  "))


def test_ollama_service_sends_prompt_to_configured_model() -> None:
    client = FakeOllamaClient()
    service = OllamaLLMService(
        base_url="http://localhost:11434",
        model="configured-test-model",
        timeout_seconds=5.0,
        generation_options={"temperature": 0.2, "num_predict": 512},
        client=client,
    )

    response = service.generate("Where is the library?")

    assert response == "The library is in Block A."
    assert client.request == {
        "model": "configured-test-model",
        "messages": [{"role": "user", "content": "Where is the library?"}],
        "options": {"temperature": 0.2, "num_predict": 512, "num_gpu": 0},
        "stream": False,
    }
