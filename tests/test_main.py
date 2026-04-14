import sqlite3

import pytest

from sc_bot import main as main_module
from sc_bot.db_metadata import get_database_version, set_database_version


class _FakeLogger:
    def info(self, _message: str) -> None:
        pass

    def error(self, _message: str, exc_info: bool = False) -> None:
        pass


def test_ensure_database_is_current_rebuilds_when_version_mismatches(monkeypatch, tmp_path, capsys) -> None:
    db_path = tmp_path / "sc_markers.db"
    db_path.touch()
    calls: list[str] = []

    monkeypatch.setattr(main_module, "DB_PATH", db_path)
    monkeypatch.setattr(main_module, "get_app_version", lambda: "0.1.0")
    monkeypatch.setattr(main_module, "get_database_version", lambda _db_path: "0.0.9")
    monkeypatch.setattr(main_module, "_rebuild_database", lambda: calls.append("rebuild") or True)

    assert main_module._ensure_database_is_current() is True
    assert calls == ["rebuild"]

    captured = capsys.readouterr()
    assert "does not match installed sc-bot 0.1.0" in captured.out


def test_ensure_database_is_current_accepts_matching_version(monkeypatch, tmp_path) -> None:
    db_path = tmp_path / "sc_markers.db"
    db_path.touch()

    monkeypatch.setattr(main_module, "DB_PATH", db_path)
    monkeypatch.setattr(main_module, "get_app_version", lambda: "0.1.0")
    monkeypatch.setattr(main_module, "get_database_version", lambda _db_path: "0.1.0")
    monkeypatch.setattr(main_module, "_rebuild_database", lambda: pytest.fail("database should not rebuild"))

    assert main_module._ensure_database_is_current() is True


def test_database_version_round_trip(tmp_path) -> None:
    db_path = tmp_path / "sc_markers.db"
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        set_database_version(cursor, "0.1.0")
        conn.commit()

    assert get_database_version(db_path) == "0.1.0"


def test_main_requires_google_api_key(monkeypatch, tmp_path, capsys) -> None:
    db_path = tmp_path / "sc_markers.db"
    db_path.touch()

    monkeypatch.setattr(main_module, "load_dotenv", lambda: None)
    monkeypatch.setattr(main_module, "_ensure_database_is_current", lambda: True)
    monkeypatch.setattr(main_module, "_maybe_import_marker_csv", lambda: None)
    monkeypatch.setattr(main_module, "DB_PATH", db_path)
    monkeypatch.setattr(main_module, "create_ai_agent", lambda _mode: pytest.fail("agent should not be created"))
    monkeypatch.setattr(main_module, "ScBotApp", lambda *args, **kwargs: pytest.fail("app should not start"))
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "legacy-key")

    main_module.main()

    captured = capsys.readouterr()
    assert "GOOGLE_API_KEY not found" in captured.out
    assert ".env.example" in captured.out


def test_main_uses_google_api_key(monkeypatch, tmp_path) -> None:
    db_path = tmp_path / "sc_markers.db"
    db_path.touch()
    fake_assist_agent = object()
    fake_fetch_agent = object()
    fake_logger = _FakeLogger()
    calls: dict[str, object] = {}

    class _FakeApp:
        def __init__(self, agents: dict[str, object], logger: object) -> None:
            calls["agents"] = agents
            calls["logger"] = logger

        def run(self) -> None:
            calls["ran"] = True

    monkeypatch.setattr(main_module, "load_dotenv", lambda: None)
    monkeypatch.setattr(main_module, "_ensure_database_is_current", lambda: True)
    monkeypatch.setattr(main_module, "_maybe_import_marker_csv", lambda: None)
    monkeypatch.setattr(main_module, "DB_PATH", db_path)
    monkeypatch.setattr(main_module, "setup_session_logger", lambda _session_id: fake_logger)
    monkeypatch.setattr(
        main_module,
        "create_ai_agent",
        lambda mode: {"assist": fake_assist_agent, "fetch": fake_fetch_agent}[mode],
    )
    monkeypatch.setattr(main_module, "ScBotApp", _FakeApp)
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    main_module.main()

    assert calls["agents"] == {"assist": fake_assist_agent, "fetch": fake_fetch_agent}
    assert calls["logger"] is fake_logger
    assert calls["ran"] is True
