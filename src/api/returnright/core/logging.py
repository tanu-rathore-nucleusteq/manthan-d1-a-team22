"""JSON logging. Every line carries the request id of the request being served, so one id from
an error response finds every log line of that request.
"""

import json
import logging
from contextvars import ContextVar
from datetime import UTC, datetime

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)

# Attributes every LogRecord has; anything else was passed with `extra=` and is logged as a field.
STANDARD_ATTRIBUTES = set(vars(logging.makeLogRecord({}))) | {"message", "asctime"}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        line = {
            "time": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_var.get(),
        }
        line.update(
            {key: value for key, value in vars(record).items() if key not in STANDARD_ATTRIBUTES}
        )
        if record.exc_info:
            line["error"] = self.formatException(record.exc_info)
        return json.dumps(line, default=str)


def configure_logging(level: str) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())
    # Uvicorn's own access log would duplicate the request line the middleware writes.
    logging.getLogger("uvicorn.access").disabled = True
