import pytest

from sc_bot import main as main_module


class _FakeLogger:
    def info(self, _message: str) -> None:
        pass

    def error(self, _message: str, exc_info: bool = False) -> None:
        pass


def test_main_requires_google_api_key(monkeypatch, tmp_path, capsys) -> None:
    db_path = tmp_path / "sc_markers.db"
    db_path.touch()

    monkeypatch.setattr(main_module, "load_dotenv", lambda: None)
    monkeypatch.setattr(main_module, "_maybe_import_marker_csv", lambda: None)
    monkeypatch.setattr(main_module, "DB_PATH", db_path)
    monkeypatch.setattr(main_module, "create_ai_agent", lambda: pytest.fail("agent should not be created"))
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
    fake_agent = object()
    fake_logger = _FakeLogger()
    calls: dict[str, object] = {}

    class _FakeApp:
        def __init__(self, agent: object, logger: object) -> None:
            calls["agent"] = agent
            calls["logger"] = logger

        def run(self) -> None:
            calls["ran"] = True

    monkeypatch.setattr(main_module, "load_dotenv", lambda: None)
    monkeypatch.setattr(main_module, "_maybe_import_marker_csv", lambda: None)
    monkeypatch.setattr(main_module, "DB_PATH", db_path)
    monkeypatch.setattr(main_module, "setup_session_logger", lambda _session_id: fake_logger)
    monkeypatch.setattr(main_module, "create_ai_agent", lambda: fake_agent)
    monkeypatch.setattr(main_module, "ScBotApp", _FakeApp)
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    main_module.main()

    assert calls["agent"] is fake_agent
    assert calls["logger"] is fake_logger
    assert calls["ran"] is True
