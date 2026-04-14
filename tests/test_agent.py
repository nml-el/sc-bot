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
        cell_types=["B cell"],
    )

    monkeypatch.setattr("sc_bot.agent.ChatGoogleGenerativeAI", lambda **_: _FakeLLM())
    monkeypatch.setattr("sc_bot.agent.ChatPromptTemplate.from_messages", lambda _messages: _FakePrompt(result))

    formatted = format_output("raw agent output", mode="assist")
    assert formatted.response_type == "general"
    assert formatted.primary_markers == []
    assert formatted.secondary_markers == []


def test_format_output_marker_mode(monkeypatch) -> None:
    result = AgentResponse(
        response_type="markers",
        response="These markers capture the core exhausted cytotoxic program.",
        primary_markers=["PDCD1", "LAG3", "HAVCR2"],
        secondary_markers=["TOX", "CXCL13"],
        cell_types=[],
    )

    monkeypatch.setattr("sc_bot.agent.ChatGoogleGenerativeAI", lambda **_: _FakeLLM())
    monkeypatch.setattr("sc_bot.agent.ChatPromptTemplate.from_messages", lambda _messages: _FakePrompt(result))

    formatted = format_output("raw marker output", mode="fetch")
    assert formatted.response_type == "markers"
    assert formatted.primary_markers == ["PDCD1", "LAG3", "HAVCR2"]
    assert formatted.secondary_markers == ["TOX", "CXCL13"]


def test_format_output_fallback_is_general(monkeypatch) -> None:
    monkeypatch.setattr("sc_bot.agent.ChatGoogleGenerativeAI", lambda **_: _FakeLLM())
    monkeypatch.setattr(
        "sc_bot.agent.ChatPromptTemplate.from_messages", lambda _messages: _FakePrompt("not-an-agent-response")
    )

    formatted = format_output("fallback raw output", mode="assist")
    assert formatted.response_type == "general"
    assert formatted.response == "fallback raw output"
    assert formatted.primary_markers == []
    assert formatted.secondary_markers == []
    assert formatted.cell_types == []


def test_format_output_passes_mode_guidance(monkeypatch) -> None:
    seen_messages: dict[str, list[tuple[str, str]]] = {}

    result = AgentResponse(
        response_type="general",
        response="Short clarification.",
        primary_markers=[],
        secondary_markers=[],
        cell_types=[],
    )

    monkeypatch.setattr("sc_bot.agent.ChatGoogleGenerativeAI", lambda **_: _FakeLLM())

    def _fake_prompt(messages: list[tuple[str, str]]) -> _FakePrompt:
        seen_messages["messages"] = messages
        return _FakePrompt(result)

    monkeypatch.setattr("sc_bot.agent.ChatPromptTemplate.from_messages", _fake_prompt)

    format_output("raw fetch output", mode="fetch")

    system_prompt = seen_messages["messages"][0][1]
    assert "This is an internal-database retrieval mode" in system_prompt


def test_format_output_passes_assist_mode_guidance(monkeypatch) -> None:
    seen_messages: dict[str, list[tuple[str, str]]] = {}

    result = AgentResponse(
        response_type="general",
        response="Short clarification.",
        primary_markers=[],
        secondary_markers=[],
        cell_types=["T cell"],
    )

    monkeypatch.setattr("sc_bot.agent.ChatGoogleGenerativeAI", lambda **_: _FakeLLM())

    def _fake_prompt(messages: list[tuple[str, str]]) -> _FakePrompt:
        seen_messages["messages"] = messages
        return _FakePrompt(result)

    monkeypatch.setattr("sc_bot.agent.ChatPromptTemplate.from_messages", _fake_prompt)

    format_output("raw assist output", mode="assist")

    system_prompt = seen_messages["messages"][0][1]
    assert "This is a conversational single-cell expert mode" in system_prompt
