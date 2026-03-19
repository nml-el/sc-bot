# Agent Guidelines & Project Setup

Welcome to the `sc-bot` project! All agents and contributors must adhere to the following setup and coding guidelines.

## 1. Package Management with `uv`

This project uses `uv` as the default Python package manager and resolver. 
- **Adding dependencies:** Use `uv add <package_name>` to add a standard dependency.
- **Adding dev dependencies:** Use `uv add --dev <package_name>` for development tools (like pytest or ruff).
- **Syncing environment:** Use `uv sync` to ensure your local virtual environment is up to date with `pyproject.toml` and `uv.lock`.
- **Running commands:** Always run scripts or tools within the `uv` environment using `uv run <command>` (e.g., `uv run python main.py` or `uv run pytest`).

## 2. Testing Setup

We use `pytest` for executing minimal tests.
- **Setup:** If not already installed, add pytest by running `uv add --dev pytest`.
- **Structure:** Place all test files inside a `tests/` directory at the project root.
- **Naming Convention:** Test files must be named starting with `test_*.py`, and test functions must start with `test_`.
- **Execution:** Run tests using `uv run pytest`.

**Example minimal test (`tests/test_main.py`):**
```python
def test_basic_addition() -> None:
    assert 1 + 1 == 2
```

## 3. Coding Style & Linting

We strictly enforce coding standards using `ruff`.

- **Linter & Formatter:** Use `ruff` to manage formatting, PEP8 compliance, and import sorting.
  - Check code: `uv run ruff check .`
  - Format code: `uv run ruff format .`
  - Fix auto-fixable issues (like import sorting): `uv run ruff check --fix .`
- **Line Length Limit:** We use a **120-character** line limit instead of the traditional 80 characters.
  *(Note: This should be reflected in the `pyproject.toml` configuration under `[tool.ruff]` with `line-length = 120`)*.
- **Type Hints:** **ALWAYS** use complete type hints in all function definitions for both arguments and return types.

**Example of expected function style:**
```python
def format_greeting(name: str, greeting_prefix: str = "Hello", repeat_count: int = 1) -> list[str]:
    """Returns a list of formatted greeting strings."""
    return [f"{greeting_prefix}, {name}!"] * repeat_count
```