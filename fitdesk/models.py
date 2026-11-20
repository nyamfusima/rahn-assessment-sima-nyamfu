"""Pydantic models for the AI's structured JSON output and the status log record."""

import json
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, StrictBool, ValidationError, model_validator

Intent = Literal["pricing", "saturday_availability", "pricing_and_availability", "other"]

Status = Literal[
    "sent",
    "rejected",
    "escalation_not_approved",
    "invalid_ai_output",
    "ai_error",
]


class InvalidAIOutput(Exception):
    """The AI response was not valid JSON or did not match the expected model."""


class EnquiryDetails(BaseModel):
    """What the customer asked about. These are labels only; facts come from the data file."""

    model_config = ConfigDict(strict=True)

    packages: list[str]
    asks_saturday_availability: StrictBool
    saturday_times: list[str]
    unsupported_requests: list[str]


class AIEnquiry(BaseModel):
    """Structured classification of one customer enquiry, as returned by Gemini."""

    model_config = ConfigDict(strict=True)

    intent: Intent
    details: EnquiryDetails
    requires_human_approval: StrictBool


def parse_ai_response(raw_text: Optional[str]) -> AIEnquiry:
    """Parse and validate the AI's raw text. Raises InvalidAIOutput on any problem."""
    if raw_text is None or not raw_text.strip():
        raise InvalidAIOutput("AI response was empty")
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise InvalidAIOutput(f"AI response was not valid JSON: {exc.msg}") from exc
    try:
        return AIEnquiry.model_validate(data)
    except ValidationError as exc:
        raise InvalidAIOutput(
            f"AI JSON did not match the expected model ({exc.error_count()} problem(s))"
        ) from exc


class StatusRecord(BaseModel):
    """One line of status_log.json."""

    timestamp: datetime
    customer_message: str
    intent: Optional[Intent] = None
    draft: Optional[str] = None
    is_escalation: bool = False
    approved: bool = False
    status: Status
    reason: Optional[str] = None

    @model_validator(mode="after")
    def sent_requires_approved_draft(self) -> "StatusRecord":
        if self.status == "sent" and not (self.approved and self.draft):
            raise ValueError("a 'sent' record needs a draft and explicit staff approval")
        if self.status != "sent" and self.approved and self.status in (
            "invalid_ai_output",
            "ai_error",
        ):
            raise ValueError("a failed AI call cannot carry an approval")
        return self
