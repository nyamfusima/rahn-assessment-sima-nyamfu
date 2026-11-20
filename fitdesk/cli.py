"""Command-line flow: read one enquiry, classify it, draft, ask for approval, log the outcome.

Order of the safety checks (SRS section 7):
1. AI call fails or times out      -> "ai_error", no draft, no approval prompt.
2. AI output invalid JSON / model  -> "invalid_ai_output", no draft, no approval prompt.
3. Draft built from the data file only (escalation phrase if facts are missing).
4. Staff must answer y for "sent"; n gives "rejected" or "escalation_not_approved".
"""

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional, Protocol

from fitdesk.approval import ask_for_approval
from fitdesk.audit_log import DEFAULT_LOG_PATH, AuditLogError, append_record, decide_status
from fitdesk.gemini_client import AIServiceError, ConfigError, GeminiClassifier, load_settings
from fitdesk.knowledge_base import DEFAULT_DATA_PATH, KnowledgeBase, KnowledgeBaseError
from fitdesk.models import InvalidAIOutput, StatusRecord, parse_ai_response
from fitdesk.response_builder import build_draft

EXIT_OK = 0
EXIT_AI_FAILURE = 1
EXIT_SETUP_ERROR = 2
EXIT_CANCELLED = 130  # conventional exit code for Ctrl+C
CANCELLED_REASON = "cancelled by staff (Ctrl+C) while waiting for the AI service"


class Classifier(Protocol):
    def classify(self, message: str) -> Optional[str]: ...


def _now() -> datetime:
    return datetime.now(timezone.utc)


def process_enquiry(
    message: str,
    classifier: Classifier,
    kb: KnowledgeBase,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
) -> StatusRecord:
    """Run one enquiry through the whole flow and return the record to log."""
    try:
        raw = classifier.classify(message)
    except AIServiceError as exc:
        output_fn(f"AI service problem: {exc}")
        output_fn("Nothing was sent.")
        return StatusRecord(timestamp=_now(), customer_message=message, status="ai_error", reason=str(exc))
    except KeyboardInterrupt:
        output_fn("")
        output_fn("Cancelled while waiting for the AI service. Nothing was sent.")
        return StatusRecord(
            timestamp=_now(),
            customer_message=message,
            status="ai_error",
            reason=CANCELLED_REASON,
        )

    try:
        enquiry = parse_ai_response(raw)
    except InvalidAIOutput as exc:
        output_fn(f"The AI returned output that could not be used: {exc} Nothing was sent.")
        return StatusRecord(
            timestamp=_now(), customer_message=message, status="invalid_ai_output", reason=str(exc)
        )

    draft = build_draft(enquiry, kb)
    approved = ask_for_approval(draft.text, draft.is_escalation, input_fn=input_fn, output_fn=output_fn)
    status, reason = decide_status(approved=approved, is_escalation=draft.is_escalation)
    return StatusRecord(
        timestamp=_now(),
        customer_message=message,
        intent=enquiry.intent,
        draft=draft.text,
        is_escalation=draft.is_escalation,
        ai_requires_human_approval=enquiry.requires_human_approval,
        approved=approved,
        status=status,
        reason=reason,
    )


def _read_message(argv: list[str], input_fn: Callable[[str], str]) -> Optional[str]:
    if argv:
        return " ".join(argv).strip()
    try:
        return input_fn("Customer message: ").strip()
    except (EOFError, KeyboardInterrupt):
        return None


def main(
    argv: Optional[list[str]] = None,
    classifier: Optional[Classifier] = None,
    kb: Optional[KnowledgeBase] = None,
    log_path: Path = DEFAULT_LOG_PATH,
    data_path: Path = DEFAULT_DATA_PATH,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
) -> int:
    """Run the assistant. Ctrl+C at any point exits cleanly, without a traceback.

    Ctrl+C before the outcome is written leaves no new record at all, so it can never be "sent".
    """
    try:
        return _run(argv, classifier, kb, log_path, data_path, input_fn, output_fn)
    except KeyboardInterrupt:
        output_fn("")
        output_fn("Cancelled. Nothing further was recorded.")
        return EXIT_CANCELLED


def _run(
    argv: Optional[list[str]] = None,
    classifier: Optional[Classifier] = None,
    kb: Optional[KnowledgeBase] = None,
    log_path: Path = DEFAULT_LOG_PATH,
    data_path: Path = DEFAULT_DATA_PATH,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
) -> int:
    argv = sys.argv[1:] if argv is None else argv

    try:
        kb = kb or KnowledgeBase.load(data_path)
    except KnowledgeBaseError as exc:
        output_fn(f"Setup error: {exc}")
        return EXIT_SETUP_ERROR

    if classifier is None:
        from dotenv import load_dotenv

        load_dotenv()
        try:
            settings = load_settings()
        except ConfigError as exc:
            output_fn(f"Setup error: {exc}")
            return EXIT_SETUP_ERROR
        classifier = GeminiClassifier(settings, [p.name for p in kb.packages])

    message = _read_message(argv, input_fn)
    if not message:
        output_fn("No customer message entered. Nothing was recorded.")
        return EXIT_SETUP_ERROR

    record = process_enquiry(message, classifier, kb, input_fn=input_fn, output_fn=output_fn)

    try:
        append_record(record, log_path)
    except AuditLogError as exc:
        output_fn(f"Log error: {exc}")
        return EXIT_SETUP_ERROR

    output_fn(f"Recorded status: {record.status} ({record.reason}).")
    if record.reason == CANCELLED_REASON:
        return EXIT_CANCELLED
    if record.status in ("ai_error", "invalid_ai_output"):
        return EXIT_AI_FAILURE
    return EXIT_OK
