import logging

import pytest

from sc_bot.models import AgentResponse, MarkerSection
from sc_bot.tui import ModeInput, ScBotApp


class _FakeAgent:
    def invoke(self, _payload: dict) -> dict:
        return {"messages": []}


def _build_app() -> ScBotApp:
    return ScBotApp(agents={"assist": _FakeAgent(), "fetch": _FakeAgent()}, logger=logging.getLogger("test"))


def test_input_placeholder_tracks_mode() -> None:
    app = _build_app()

    assert "Assist mode" in app._input_placeholder()
    assert "Mode: Assist" in app._mode_status_text()
    assert "Model:" in app._mode_status_text()

    app.mode = "fetch"
    assert "Fetch mode" in app._input_placeholder()
    assert "Mode: Fetch" in app._mode_status_text()


def test_action_toggle_mode_switches_between_assist_and_fetch(monkeypatch: pytest.MonkeyPatch) -> None:
    app = _build_app()
    seen_modes: list[str] = []

    monkeypatch.setattr(app, "_set_mode", lambda mode: seen_modes.append(mode))

    app.mode = "assist"
    app.action_toggle_mode()
    app.mode = "fetch"
    app.action_toggle_mode()

    assert seen_modes == ["fetch", "assist"]


def test_mode_input_binds_tab_to_toggle_mode() -> None:
    assert ("tab", "app.toggle_mode") in [(binding.key, binding.action) for binding in ModeInput.BINDINGS]


def test_handle_mode_command_switches_to_assist(monkeypatch: pytest.MonkeyPatch) -> None:
    app = _build_app()
    messages: list[str] = []

    monkeypatch.setattr(app, "_set_mode", lambda mode: setattr(app, "mode", mode))
    monkeypatch.setattr(app, "_render_system_message", lambda message: messages.append(message))

    app.mode = "fetch"
    assert app._handle_mode_command("/assist") is True
    assert app.mode == "assist"
    assert "assist" in messages[0].lower()


def test_handle_mode_command_switches_to_fetch(monkeypatch: pytest.MonkeyPatch) -> None:
    app = _build_app()
    messages: list[str] = []

    monkeypatch.setattr(app, "_set_mode", lambda mode: setattr(app, "mode", mode))
    monkeypatch.setattr(app, "_render_system_message", lambda message: messages.append(message))

    assert app.mode == "assist"
    assert app._handle_mode_command("/fetch") is True
    assert app.mode == "fetch"
    assert "fetch" in messages[0].lower()


def test_handle_mode_command_ignores_removed_mode_command(monkeypatch: pytest.MonkeyPatch) -> None:
    app = _build_app()
    messages: list[str] = []

    monkeypatch.setattr(app, "_render_system_message", lambda message: messages.append(message))

    app.mode = "fetch"
    assert app._handle_mode_command("/mode") is False
    assert messages == []


def test_highlight_response_terms_wraps_markers_and_assist_cell_types() -> None:
    app = _build_app()
    response = AgentResponse(
        response_type="general",
        response="T cell programs often include CD3E and IL7R, while memory T cell labels can overlap.",
        marker_sections=[
            MarkerSection(label="Primary Canonical Markers", genes=["CD3E"]),
            MarkerSection(label="Secondary/Supportive Markers", genes=["IL7R"]),
        ],
        cell_types=["T cell", "memory T cell"],
    )

    highlighted = app._highlight_response_terms(response.response, response, mode="assist")

    assert "`CD3E`" in highlighted
    assert "`IL7R`" in highlighted
    assert "`memory T cell`" in highlighted
    assert "`T cell` programs" in highlighted


def test_highlight_response_terms_skips_cell_types_in_fetch_mode() -> None:
    app = _build_app()
    response = AgentResponse(
        response_type="markers",
        response="T cell markers include CD3E.",
        marker_sections=[
            MarkerSection(label="Primary Canonical Markers", genes=["CD3E"]),
        ],
        cell_types=["T cell"],
    )

    highlighted = app._highlight_response_terms(response.response, response, mode="fetch")

    assert "`CD3E`" in highlighted
    assert "`T cell`" not in highlighted


def test_chat_message_stores_marker_sections_for_copy() -> None:
    """ChatMessage with marker_sections stores tuples for per-section copy buttons."""
    from sc_bot.tui import ChatMessage

    sections = [
        ("Primary Canonical Markers", '["CD3E", "CD4"]', '[\n  "CD3E",\n  "CD4"\n]'),
        ("Secondary/Supportive Markers", '["FOXP3"]', '[\n  "FOXP3"\n]'),
    ]
    widget = ChatMessage("Test", role="ai", marker_sections=sections, copy_all_text='{"all": true}')

    assert widget.marker_sections is not None
    assert len(widget.marker_sections) == 2
    assert widget.marker_sections[0][0] == "Primary Canonical Markers"
    assert widget.marker_sections[1][2] == '[\n  "FOXP3"\n]'
    assert widget.copy_all_text == '{"all": true}'


def test_chat_message_marker_sections_with_special_characters_in_label() -> None:
    """Labels with special characters (slashes, parens) should be stored and handled correctly."""
    from sc_bot.tui import ChatMessage

    sections = [
        ("Myeloid/Macrophage Primary Markers", '["CD68"]', '[\n  "CD68"\n]'),
        ("Smooth Muscle (Vascular) Primary Markers", '["ACTA2"]', '[\n  "ACTA2"\n]'),
    ]
    widget = ChatMessage("Test", role="ai", marker_sections=sections)

    assert widget.marker_sections is not None
    assert len(widget.marker_sections) == 2
    assert "/" in widget.marker_sections[0][0]
    assert "(" in widget.marker_sections[1][0]
