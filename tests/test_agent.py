from pathlib import Path

from sc_bot.agent import format_output, _is_simple_response
from sc_bot.models import AgentResponse, MarkerSection
from sc_bot.system_prompt import build_system_prompt


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
        marker_sections=[],
        cell_types=["B cell"],
    )

    monkeypatch.setattr("sc_bot.agent.ChatGoogleGenerativeAI", lambda **_: _FakeLLM())
    monkeypatch.setattr("sc_bot.agent.ChatPromptTemplate.from_messages", lambda _messages: _FakePrompt(result))

    formatted = format_output("raw agent output", mode="assist")
    assert formatted.response_type == "general"
    assert formatted.marker_sections == []


def test_format_output_marker_mode(monkeypatch) -> None:
    result = AgentResponse(
        response_type="markers",
        response="These markers capture the core exhausted cytotoxic program.",
        marker_sections=[
            MarkerSection(label="Primary Canonical Markers", genes=["PDCD1", "LAG3", "HAVCR2"]),
            MarkerSection(label="Secondary/Supportive Markers", genes=["TOX", "CXCL13"]),
        ],
        cell_types=[],
    )

    monkeypatch.setattr("sc_bot.agent.ChatGoogleGenerativeAI", lambda **_: _FakeLLM())
    monkeypatch.setattr("sc_bot.agent.ChatPromptTemplate.from_messages", lambda _messages: _FakePrompt(result))

    formatted = format_output("raw marker output", mode="fetch")
    assert formatted.response_type == "markers"
    assert len(formatted.marker_sections) == 2
    assert formatted.marker_sections[0].label == "Primary Canonical Markers"
    assert formatted.marker_sections[0].genes == ["PDCD1", "LAG3", "HAVCR2"]
    assert formatted.marker_sections[1].label == "Secondary/Supportive Markers"
    assert formatted.marker_sections[1].genes == ["TOX", "CXCL13"]


def test_format_output_cell_type_specific_sections(monkeypatch) -> None:
    result = AgentResponse(
        response_type="markers",
        response="Differentiating markers for the two cell types.",
        marker_sections=[
            MarkerSection(label="Epithelial cell Markers", genes=["EPCAM", "KRT8"]),
            MarkerSection(label="Endothelial cell Markers", genes=["PECAM1", "VWF"]),
        ],
        cell_types=[],
    )

    monkeypatch.setattr("sc_bot.agent.ChatGoogleGenerativeAI", lambda **_: _FakeLLM())
    monkeypatch.setattr("sc_bot.agent.ChatPromptTemplate.from_messages", lambda _messages: _FakePrompt(result))

    formatted = format_output("raw differentiating output", mode="fetch")
    assert formatted.response_type == "markers"
    assert len(formatted.marker_sections) == 2
    assert formatted.marker_sections[0].label == "Epithelial cell Markers"
    assert formatted.marker_sections[1].label == "Endothelial cell Markers"


def test_format_output_fallback_is_general(monkeypatch) -> None:
    monkeypatch.setattr("sc_bot.agent.ChatGoogleGenerativeAI", lambda **_: _FakeLLM())
    monkeypatch.setattr(
        "sc_bot.agent.ChatPromptTemplate.from_messages", lambda _messages: _FakePrompt("not-an-agent-response")
    )

    formatted = format_output("fallback raw output", mode="assist")
    assert formatted.response_type == "general"
    assert formatted.response == "fallback raw output"


def test_format_output_empty_input_returns_fallback() -> None:
    """Empty or whitespace-only input should return a general fallback without calling the LLM."""
    for empty_input in ["", "   "]:
        formatted = format_output(empty_input, mode="assist")
        assert formatted.response_type == "general"
        assert formatted.marker_sections == []
        assert formatted.cell_types == []


def test_format_output_passes_mode_guidance(monkeypatch) -> None:
    seen_messages: dict[str, list[tuple[str, str]]] = {}

    result = AgentResponse(
        response_type="general",
        response="Short clarification.",
        marker_sections=[],
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
        marker_sections=[],
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
    assert "draw on your knowledge of gene functions" in system_prompt


def test_build_system_prompt_includes_assist_example_template() -> None:
    template_path = Path(__file__).resolve().parents[1] / "examples" / "assist_mode_template.md"
    template = template_path.read_text(encoding="utf-8").rstrip()

    system_prompt = build_system_prompt("assist")

    assert template in system_prompt
    assert "### Session Mode: Assist" in system_prompt


def test_build_system_prompt_includes_fetch_example_template() -> None:
    template_path = Path(__file__).resolve().parents[1] / "examples" / "fetch_mode_template.md"
    template = template_path.read_text(encoding="utf-8").rstrip()

    system_prompt = build_system_prompt("fetch")

    assert template in system_prompt
    assert "### Session Mode: Fetch" in system_prompt


def test_is_simple_response_false_for_consensus_data() -> None:
    """Messages with source_count / tissue_count signals should NOT be simple."""
    raw = "EPCAM source_count=12, tissue_count=5\nKRT8 source_count=10"
    assert _is_simple_response(raw) is False


def test_is_simple_response_false_for_python_code_block() -> None:
    """Messages with ```python gene lists should NOT be simple."""
    raw = '**Primary Canonical Markers:**\n```python\n["EPCAM", "KRT8"]\n```'
    assert _is_simple_response(raw) is False


def test_is_simple_response_true_for_alias_response() -> None:
    """Simple alias mapping responses should be detected as simple."""
    raw = "**Gene Alias Mapping**\n\n* **PD-1** → `PDCD1`\n* **CD16** → `FCGR3A`"
    assert _is_simple_response(raw) is True


def test_is_simple_response_true_for_greeting() -> None:
    """Conversational greetings should be detected as simple."""
    raw = "Hello! How can I help you with your single-cell analysis today?"
    assert _is_simple_response(raw) is True


def test_is_simple_response_false_for_unknown_format() -> None:
    """Unknown formats should default to not-simple (safe default: run extraction)."""
    raw = "The top markers for this cluster are EPCAM and KRT8 based on differential expression."
    assert _is_simple_response(raw) is False


def test_format_output_fast_path_preserves_alias_verbatim() -> None:
    """Alias responses should pass through verbatim without an LLM call."""
    raw = "**Gene Alias Mapping**\n\n* **PD-1** → `PDCD1`\n* **CD16** → `FCGR3A`"
    result = format_output(raw, mode="assist")
    assert result.response_type == "general"
    assert result.response == raw
    assert result.marker_sections == []


def test_format_output_fast_path_preserves_greeting_verbatim() -> None:
    """Greetings should pass through verbatim without an LLM call."""
    raw = "Hello! How can I help you with your single-cell analysis today?"
    result = format_output(raw, mode="assist")
    assert result.response == raw
