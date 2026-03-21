import os
import uuid
from dotenv import load_dotenv

from sc_bot.agent import create_ai_agent
from sc_bot.config import DB_PATH
from sc_bot.logger import setup_session_logger
from sc_bot.tui import ScBotApp


def main() -> None:
    # Load environment variables (e.g., GEMINI_API_KEY)
    load_dotenv()

    if not DB_PATH.exists():
        print(f"Error: Database not found at {DB_PATH}")
        print("Please run 'uv run python scripts/setup_db.py' to initialize the database.")
        return

    if not os.environ.get("GEMINI_API_KEY"):
        print("Error: GEMINI_API_KEY not found in .env file or environment variables.")
        print("Please add your key to a .env file: GEMINI_API_KEY=your_key_here")
        return

    session_id = uuid.uuid4().hex
    logger = setup_session_logger(session_id)
    logger.info("Session started (TUI Mode).")

    try:
        agent = create_ai_agent()
        app = ScBotApp(agent=agent, logger=logger)
        app.run()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        print(f"A fatal error occurred. Check logs at session_{session_id}.log")


if __name__ == "__main__":
    main()
