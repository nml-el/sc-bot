import logging

from sc_bot.config import LOGS_DIR


def setup_session_logger(session_id: str) -> logging.Logger:
    """
    Sets up and returns a logger instance for a specific session ID.

    Args:
        session_id (str): The unique identifier for the session.

    Returns:
        logging.Logger: The configured logger instance.

    Example:
        Input: setup_session_logger("abc-123")
        Output: <Logger session_abc-123 (INFO)>
    """
    log_file = LOGS_DIR / f"session_{session_id}.log"

    logger = logging.getLogger(f"session_{session_id}")
    logger.setLevel(logging.INFO)

    # Avoid adding handlers multiple times if the logger is requested again
    if not logger.handlers:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)

        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        file_handler.setFormatter(formatter)

        logger.addHandler(file_handler)

    return logger
