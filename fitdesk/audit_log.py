"""Appends outcomes to status_log.json and decides when "sent" may be recorded (FR-06).

The log is a local JSON array, one object per enquiry. It is git-ignored and never committed.
"""

import json
import os
from pathlib import Path

from fitdesk.models import Status, StatusRecord

DEFAULT_LOG_PATH = Path(__file__).resolve().parent.parent / "status_log.json"


class AuditLogError(Exception):
    """The existing log cannot be read safely, or the new record cannot be written."""


def decide_status(approved: bool, is_escalation: bool) -> tuple[Status, str]:
    """Status for a valid, successfully drafted enquiry.

    AI failures never reach this function; they are recorded as "ai_error" or
    "invalid_ai_output" by the caller and can never be "sent".
    """
    if approved:
        if is_escalation:
            return "sent", "staff approved the escalation message"
        return "sent", "staff approved the draft"
    if is_escalation:
        return "escalation_not_approved", "staff answered n to the escalation message"
    return "rejected", "staff answered n"


def read_records(path: Path = DEFAULT_LOG_PATH) -> list[dict]:
    path = Path(path)
    if not path.exists():
        return []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise AuditLogError(f"Cannot read status log {path}: {exc}") from exc
    if not text.strip():
        return []
    try:
        records = json.loads(text)
    except json.JSONDecodeError as exc:
        raise AuditLogError(
            f"Status log {path} is not valid JSON; it was left unchanged. Fix or move it and try again."
        ) from exc
    if not isinstance(records, list):
        raise AuditLogError(f"Status log {path} is not a JSON list; it was left unchanged.")
    return records


def append_record(record: StatusRecord, path: Path = DEFAULT_LOG_PATH) -> None:
    """Append one record. Writes to a temporary file first so a crash cannot corrupt the log."""
    path = Path(path)
    records = read_records(path)
    records.append(record.model_dump(mode="json"))
    tmp_path = path.with_name(path.name + ".tmp")
    try:
        tmp_path.write_text(json.dumps(records, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        os.replace(tmp_path, path)
    except OSError as exc:
        raise AuditLogError(f"Cannot write status log {path}: {exc}") from exc
