# logger.py
import logging
from pathlib import Path
from logging.handlers import RotatingFileHandler

LOG_FILE = Path("logs/app.log")

def get_logger(name: str) -> logging.Logger:
    log = logging.getLogger(name)

    if not log.handlers:
        log.setLevel(logging.DEBUG)

        # clear the log file on first setup
        LOG_FILE.write_text("")

        handler = RotatingFileHandler(LOG_FILE, maxBytes=5_000_000, backupCount=3)
        handler.setFormatter(logging.Formatter("[%(name)s] [%(levelname)s] %(message)s"))
        log.addHandler(handler)

    return log