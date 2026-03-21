"""
Configuration settings for the sc-bot project.
"""

from pathlib import Path

# Get the absolute path to the project root (2 levels up from this file)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Database configuration
DB_PATH: str = str(PROJECT_ROOT / "data" / "sc_markers.db")

# LLM configuration
LLM_MODEL: str = "gemini-2.5-flash-lite"
