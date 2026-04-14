import logging

import pytest

from sc_bot.models import AgentResponse
from sc_bot.tui import ModeInput, ScBotApp


class _FakeAgent:
    def invoke(self, _payload: dict) -> dict:
        return {"messages": []}


def _build_app() -> ScBotApp:
    return ScBotApp(agents={"assist": _FakeAgent(), "fetch": _FakeAgent()}, logger=logging.getLogger("test"))


def test_input_placeholder_tracks_mode() -> None:
    app = _build_app()

    assert "Assist mode" in app._input_placeholder()
    assert app._mode_status_text() == "Mode: assist"

    app.mode = "fetch"
    assert "Fetch mode" in app._input_placeholder()
    assert app._mode_status_text() == "Mode: fetch"


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
        primary_markers=["CD3E"],
        secondary_markers=["IL7R"],
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
        primary_markers=["CD3E"],
        secondary_markers=[],
        cell_types=["T cell"],
    )

    highlighted = app._highlight_response_terms(response.response, response, mode="fetch")

    assert "`CD3E`" in highlighted
    assert "`T cell`" not in highlighted
