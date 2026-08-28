import logging
import queue
import sys
from datetime import datetime
from pathlib import Path
from config import LOGS_DIR

# Thread-safe log queue for GUI streaming
log_queue = queue.Queue()

class QueueHandler(logging.Handler):
    """Logging handler that emits log records to a thread-safe Queue for GUI streaming."""
    def __init__(self, log_q):
        super().__init__()
        self.log_q = log_q

    def emit(self, record):
        try:
            msg = self.format(record)
            self.log_q.put((record.levelname, msg))
        except Exception:
            self.handleError(record)

class CustomFormatter(logging.Formatter):
    """Formatted log string: [TAG/LEVEL] Timestamp - Message"""
    def format(self, record):
        time_str = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
        tag = getattr(record, "tag", record.levelname)
        return f"[{tag}] {time_str} - {record.getMessage()}"

def setup_logger(name="FB_AutoViral"):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    if logger.handlers:
        return logger

    formatter = CustomFormatter()

    # Console output handler
    if sys.stdout is not None:
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.INFO)
        ch.setFormatter(formatter)
        logger.addHandler(ch)

    # File output handler
    log_file = LOGS_DIR / f"app_{datetime.now().strftime('%Y%m%d')}.log"
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    # GUI Queue handler
    qh = QueueHandler(log_queue)
    qh.setLevel(logging.INFO)
    qh.setFormatter(formatter)
    logger.addHandler(qh)

    return logger

logger = setup_logger()

def log_info(msg, tag="SYSTEM"):
    logger.info(msg, extra={"tag": tag})

def log_error(msg, tag="ERROR"):
    logger.error(msg, extra={"tag": tag})

def log_warning(msg, tag="WARN"):
    logger.warning(msg, extra={"tag": tag})

def log_debug(msg, tag="DEBUG"):
    logger.debug(msg, extra={"tag": tag})
