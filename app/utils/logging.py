# app/utils/logging.py
import json
import logging
import sys
from typing import Optional, Any, Dict
from fastapi import Request

# ---------- Structured JSON Logging ----------


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: Dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S.%fZ"),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }
        # Optional request context
        if hasattr(record, "path"):
            payload["path"] = record.path
        if hasattr(record, "method"):
            payload["method"] = record.method
        if hasattr(record, "status"):
            payload["status"] = record.status
        if hasattr(record, "tenant"):
            payload["tenant"] = record.tenant
        if hasattr(record, "request_id"):
            payload["request_id"] = record.request_id
        if hasattr(record, "duration_ms"):
            payload["duration_ms"] = record.duration_ms
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def setup_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.setLevel(level)
    root.handlers = [handler]


# ---------- Helpers to attach request context ----------
def get_request_context(
    request: Optional[Request] = None, duration_ms: Optional[float] = None
) -> Dict[str, Any]:
    context: Dict[str, Any] = {}
    if request:
        context.update(
            {
                "path": request.url.path,
                "method": request.method,
                "tenant": request.headers.get("X-Tenant-ID", "unknown"),
                "request_id": request.headers.get("X-Request-ID", "none"),
            }
        )
    if duration_ms is not None:
        context["duration_ms"] = float(round(duration_ms, 2))  # ensure type is float
    return context
