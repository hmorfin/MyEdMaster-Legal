# ai/logging_config.py
"""
Central logging configuration for the AI service.

Design goals
------------
- Structured, single-line JSON logs to stdout (Docker-friendly: `docker compose logs -f ai`)
  AND to a rotating log file on disk, so logs are still available after a crash or after
  `docker compose down` has thrown away the container's console output.
- Consistent format everywhere — any module just does `logging.getLogger(__name__)`
  and inherits this configuration automatically once `configure_logging()` has run.
- Correlation: every inbound HTTP request gets a short request_id (via middleware in
  main.py) that is attached to every log line emitted while handling that request.

Where the log file lives
-------------------------
By default: `ai/logs/ai-service.log` (resolved relative to this file, i.e. `/app/logs/`
inside the container). `docker-compose.yml` bind-mounts `./ai/logs` on the host to
`/app/logs` in the `ai` container, so the file is readable directly from the host at
`legal/ai/logs/ai-service.log` and survives container restarts/recreation. It rotates at
~10MB with 5 backups kept (~60MB max on disk) — see LOG_FILE_MAX_BYTES / LOG_FILE_BACKUP_COUNT
below to change that. Set LOG_TO_FILE=false to disable file logging (stdout only).

Sensitive-data policy
----------------------
This module only controls *how* logs are formatted/shipped. It is the responsibility
of every call site to never pass raw user queries, document text, LLM prompts/responses,
PII, or credentials (API keys, AWS secrets, S3 URLs with signatures, etc.) as log
messages or `extra` fields. Log counts, lengths, ids, booleans, scores and durations
instead of raw content.
"""

import contextvars
import json
import logging
import logging.handlers
import os
import sys
import time
from pathlib import Path

# Holds the current request's short id, set by the request-logging middleware in
# main.py. Falls back to "-" for code paths that run outside an HTTP request (e.g.
# the corpus_ingestion.py offline script, or app startup).
request_id_ctx_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id", default="-"
)


class RequestIdFilter(logging.Filter):
    """Injects the current request_id (if any) into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx_var.get()
        return True


class JsonFormatter(logging.Formatter):
    """Renders each log record as a single-line JSON object.

    Includes timestamp, level, logger name, request id, message, and any extra
    structured fields passed via `logger.info(msg, extra={...})`.
    """

    # Fields already present on a bare LogRecord — everything else in __dict__ is
    # an "extra" field the caller passed in and should be surfaced in the JSON.
    _RESERVED = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys()) | {
        "request_id",
        "message",
        "asctime",
    }

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "request_id": getattr(record, "request_id", "-"),
            "message": record.getMessage(),
        }

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        for key, value in record.__dict__.items():
            if key not in self._RESERVED:
                payload[key] = value

        return json.dumps(payload, default=str)


def _build_file_handler() -> logging.Handler | None:
    """Builds the rotating file handler, or returns None if file logging is disabled
    or the log directory/file can't be created (e.g. read-only filesystem) — in which
    case we fall back to stdout-only rather than crashing the whole service on startup.
    """
    if os.getenv("LOG_TO_FILE", "true").strip().lower() in ("false", "0", "no"):
        return None

    log_dir = os.getenv("LOG_DIR", "logs")
    log_file_name = os.getenv("LOG_FILE_NAME", "ai-service.log")
    max_bytes = int(os.getenv("LOG_FILE_MAX_BYTES", 10 * 1024 * 1024))  # 10MB per file
    backup_count = int(os.getenv("LOG_FILE_BACKUP_COUNT", 5))  # ~60MB total on disk

    # Resolve relative to this file (ai/logging_config.py) rather than cwd, so the
    # path is stable regardless of how/where uvicorn is launched from.
    log_dir_path = Path(log_dir)
    if not log_dir_path.is_absolute():
        log_dir_path = Path(__file__).resolve().parent / log_dir_path

    try:
        log_dir_path.mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            filename=str(log_dir_path / log_file_name),
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
    except OSError:
        # Don't take the service down just because the log file couldn't be opened —
        # stdout logging (captured by `docker compose logs`) still works.
        logging.getLogger(__name__).warning(
            "log_file_handler_setup_failed", exc_info=True, extra={"log_dir": str(log_dir_path)}
        )
        return None

    file_handler.setFormatter(JsonFormatter())
    file_handler.addFilter(RequestIdFilter())
    return file_handler


def configure_logging() -> None:
    """Idempotently configure root logging for the AI service.

    Reads LOG_LEVEL from the environment (default INFO). Safe to call more than once
    (e.g. once from main.py under uvicorn, once from a standalone script).
    """
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    root = logging.getLogger()
    if getattr(root, "_ai_service_configured", False):
        root.setLevel(level)
        return

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(JsonFormatter())
    stdout_handler.addFilter(RequestIdFilter())

    handlers = [stdout_handler]
    file_handler = _build_file_handler()
    if file_handler is not None:
        handlers.append(file_handler)

    root.handlers = handlers
    root.setLevel(level)

    # Quiet down noisy third-party libraries unless LOG_LEVEL explicitly asks for more.
    for noisy_logger in ("httpx", "httpcore", "urllib3", "botocore", "boto3", "s3transfer"):
        logging.getLogger(noisy_logger).setLevel(max(level, logging.WARNING))

    root._ai_service_configured = True

    logging.getLogger(__name__).info(
        "logging_configured",
        extra={
            "log_level": level_name,
            "log_file": getattr(file_handler, "baseFilename", None),
        },
    )


def log_timing(logger: logging.Logger, event: str, start_time: float, **fields) -> None:
    """Convenience helper: log `event` with an auto-computed duration_ms field."""
    duration_ms = round((time.time() - start_time) * 1000, 1)
    logger.info(event, extra={"duration_ms": duration_ms, **fields})