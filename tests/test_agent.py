from sc_bot.agent import format_output
from sc_bot.models import AgentResponse


class _FakeChain:
    def __init__(self, result):
        self._result = result

    def invoke(self, _: dict):
        return self._result


class _FakePrompt:
    def __init__(self, result):
        self._result = result

    def __or__(self, _other):
        return _FakeChain(self._result)


class _FakeLLM:
    def with_structured_output(self, _schema):
        return object()


def test_format_output_general_mode(monkeypatch) -> None:
    result = AgentResponse(
        response_type="general",
        response="This gene set is most consistent with a B-cell-like program and likely reflects a stable identity rather than a transient state.",
        primary_markers=[],
        secondary_markers=[],
    )

    monkeypatch.setattr("sc_bot.agent.ChatGoogleGenerativeAI", lambda **_: _FakeLLM())
    monkeypatch.setattr("sc_bot.agent.ChatPromptTemplate.from_messages", lambda _messages: _FakePrompt(result))

    formatted = format_output("raw agent output")
    assert formatted.response_type == "general"
    assert formatted.primary_markers == []
    assert formatted.secondary_markers == []


def test_format_output_marker_mode(monkeypatch) -> None:
    result = AgentResponse(
        response_type="markers",
        response="These markers capture the core exhausted cytotoxic program.",
        primary_markers=["PDCD1", "LAG3", "HAVCR2"],
        secondary_markers=["TOX", "CXCL13"],
    )

    monkeypatch.setattr("sc_bot.agent.ChatGoogleGenerativeAI", lambda **_: _FakeLLM())
    monkeypatch.setattr("sc_bot.agent.ChatPromptTemplate.from_messages", lambda _messages: _FakePrompt(result))

    formatted = format_output("raw marker output")
    assert formatted.response_type == "markers"
    assert formatted.primary_markers == ["PDCD1", "LAG3", "HAVCR2"]
    assert formatted.secondary_markers == ["TOX", "CXCL13"]


def test_format_output_fallback_is_general(monkeypatch) -> None:
    monkeypatch.setattr("sc_bot.agent.ChatGoogleGenerativeAI", lambda **_: _FakeLLM())
    monkeypatch.setattr(
        "sc_bot.agent.ChatPromptTemplate.from_messages", lambda _messages: _FakePrompt("not-an-agent-response")
    )

    formatted = format_output("fallback raw output")
    assert formatted.response_type == "general"
    assert formatted.response == "fallback raw output"
    assert formatted.primary_markers == []
    assert formatted.secondary_markers == []
