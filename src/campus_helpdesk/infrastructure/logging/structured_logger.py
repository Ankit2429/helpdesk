import logging
import json
import uuid
import time
from typing import Any, Dict

class StructuredLogger:
    """Simple structured logger that emits one JSON line per event.
    Usage:
        logger = StructuredLogger.get_logger()
        logger.log_event(request_id, session_id, **fields)
    """

    _logger: logging.Logger = None

    @classmethod
    def get_logger(cls) -> "StructuredLogger":
        if cls._logger is None:
            logger = logging.getLogger("structured_logger")
            logger.setLevel(logging.INFO)
            handler = logging.StreamHandler()
            formatter = logging.Formatter("%(message)s")
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            cls._logger = logger
        return cls()

    def log_event(self, request_id: str, session_id: str, **fields: Any) -> None:
        entry: Dict[str, Any] = {
            "request_id": request_id,
            "session_id": session_id,
            "timestamp": time.time(),
        }
        entry.update(fields)
        # Emit as a single JSON line
        self._logger.info(json.dumps(entry))
