"""
Configuration settings for the sc-bot project.
"""

from pathlib import Path

# Base directory for the CLI tool data and logs in the user's home directory
SC_BOT_DIR = Path.home() / ".sc-bot"

# Database configuration
DB_PATH = SC_BOT_DIR / "sc_markers.db"

# Logs configuration
LOGS_DIR = SC_BOT_DIR / "logs"

# LLM configuration
LLM_MODEL: str = "gemini-2.5-flash-lite"

# Ensure the base directories exist
SC_BOT_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)
