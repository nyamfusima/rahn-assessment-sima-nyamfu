"""Thin wrapper around the Gemini API; the only module that talks to the network (FR-02).

Gemini only classifies the enquiry into structured JSON. It never writes the reply and is
never asked for prices or availability. Its raw text is returned to the caller, which
validates it with the Pydantic model in fitdesk.models (it is never trusted as-is).
"""

import os
import re
from dataclasses import dataclass
from typing import Any, Optional

DEFAULT_TIMEOUT_SECONDS = 30.0
_PLACEHOLDER_VALUES = {"", "your_api_key_here", "your_gemini_model_name_here"}

# Bounded retries, done by the SDK's own HttpRetryOptions (google-genai 3.x).
# 3 attempts in total (1 call + at most 2 retries), only for transient HTTP errors.
# 400, 401, 403 and 404 are permanent and are never retried.
RETRY_ATTEMPTS = 3
RETRY_INITIAL_DELAY_SECONDS = 1.0
RETRY_MAX_DELAY_SECONDS = 8.0
RETRY_STATUS_CODES = [429, 500, 502, 503, 504]
_TIMEOUT_STATUS_CODES = {408, 504}

_MAX_ERROR_MESSAGE_CHARS = 200
_KEY_PATTERNS = [
    re.compile(r"AIza[0-9A-Za-z_\-]{20,}"),  # Google API key format
    re.compile(r"(?i)(key=)[^&\s]+"),  # key passed as a URL parameter
]


class ConfigError(Exception):
    """GEMINI_API_KEY or GEMINI_MODEL is missing or still a placeholder."""


class AIServiceError(Exception):
    """The Gemini call failed or timed out. Never leads to a "sent" record."""

    def __init__(self, message: str, timed_out: bool = False, status_code: Optional[int] = None) -> None:
        super().__init__(message)
        self.timed_out = timed_out
        self.status_code = status_code


def sanitise_error_message(text: Any, secret: str = "") -> str:
    """One short line with any API key removed. Used only for Google's error message text."""
    cleaned = " ".join(str(text or "").split())
    if secret:
        cleaned = cleaned.replace(secret, "[REDACTED]")
    for pattern in _KEY_PATTERNS:
        cleaned = pattern.sub(lambda m: (m.group(1) if m.groups() else "") + "[REDACTED]", cleaned)
    if len(cleaned) > _MAX_ERROR_MESSAGE_CHARS:
        cleaned = cleaned[: _MAX_ERROR_MESSAGE_CHARS - 3] + "..."
    return cleaned or "no message"


@dataclass(frozen=True)
class GeminiSettings:
    api_key: str
    model: str
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS


def load_settings() -> GeminiSettings:
    """Read settings from the environment (.env is loaded by the caller)."""
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    model = os.getenv("GEMINI_MODEL", "").strip()
    if api_key in _PLACEHOLDER_VALUES:
        raise ConfigError("GEMINI_API_KEY is not set. Copy .env.example to .env and add your key.")
    if model in _PLACEHOLDER_VALUES:
        raise ConfigError("GEMINI_MODEL is not set. Add a Gemini model name available to your key to .env.")
    timeout_text = os.getenv("GEMINI_TIMEOUT_SECONDS", "").strip()
    try:
        timeout = float(timeout_text) if timeout_text else DEFAULT_TIMEOUT_SECONDS
    except ValueError as exc:
        raise ConfigError("GEMINI_TIMEOUT_SECONDS must be a number of seconds.") from exc
    if timeout <= 0:
        raise ConfigError("GEMINI_TIMEOUT_SECONDS must be greater than 0.")
    return GeminiSettings(api_key=api_key, model=model, timeout_seconds=timeout)


# Plain JSON Schema (no $ref) sent to Gemini's structured output. The response is still
# validated locally by fitdesk.models.AIEnquiry, which is the real contract.
RESPONSE_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "intent": {
            "type": "string",
            "enum": ["pricing", "saturday_availability", "pricing_and_availability", "other"],
        },
        "details": {
            "type": "object",
            "properties": {
                "packages": {"type": "array", "items": {"type": "string"}},
                "asks_saturday_availability": {"type": "boolean"},
                "saturday_times": {"type": "array", "items": {"type": "string"}},
                "unsupported_requests": {"type": "array", "items": {"type": "string"}},
            },
            "required": [
                "packages",
                "asks_saturday_availability",
                "saturday_times",
                "unsupported_requests",
            ],
        },
        "requires_human_approval": {"type": "boolean"},
    },
    "required": ["intent", "details", "requires_human_approval"],
}


def build_system_instruction(package_names: list[str]) -> str:
    names = ", ".join(f'"{n}"' for n in package_names) or "(none)"
    return (
        "You classify customer enquiries for a small fitness studio. "
        "You do NOT answer the customer and you must NOT state or guess any price, time, date or availability. "
        "Return only JSON matching the schema.\n"
        "- intent: 'pricing' (package prices), 'saturday_availability' (Saturday slots), "
        "'pricing_and_availability' (both), or 'other' (anything else).\n"
        f"- details.packages: each package the customer asks about. Known package names are {names}. "
        "Use the known name when it clearly matches; otherwise copy the customer's wording "
        "(for example '20 sessions'). Empty list if they ask about prices in general.\n"
        "- details.asks_saturday_availability: true if they ask about Saturday slots.\n"
        "- details.saturday_times: specific Saturday times asked about, in 24-hour HH:MM format. "
        "Empty list if no specific time.\n"
        "- details.unsupported_requests: short labels for anything else asked for that is not a package "
        "price or a Saturday slot (for example other days, bookings, payments, discounts, location).\n"
        "- requires_human_approval: always true."
    )


class GeminiClassifier:
    """Calls Gemini once per enquiry and returns the raw response text."""

    def __init__(self, settings: GeminiSettings, package_names: list[str], client: Optional[Any] = None) -> None:
        self._settings = settings
        self._system_instruction = build_system_instruction(package_names)
        self._client = client

    def _get_client(self) -> Any:
        if self._client is None:
            from google import genai

            self._client = genai.Client(
                api_key=self._settings.api_key,
                http_options=build_http_options(self._settings),
            )
        return self._client

    def classify(self, message: str) -> Optional[str]:
        """Return Gemini's raw JSON text. Raises AIServiceError on any failure or timeout.

        KeyboardInterrupt (Ctrl+C) is not an Exception subclass, so it is deliberately not
        caught here; the CLI handles it and records the enquiry as not sent.
        """
        try:
            from google.genai import types

            config = types.GenerateContentConfig(
                system_instruction=self._system_instruction,
                response_mime_type="application/json",
                response_json_schema=RESPONSE_JSON_SCHEMA,
                temperature=0,
            )
            response = self._get_client().models.generate_content(
                model=self._settings.model,
                contents=message,
                config=config,
            )
            return response.text
        except Exception as exc:  # SDK, httpx and timeout errors all end here
            raise self._to_service_error(exc) from exc

    def _to_service_error(self, exc: Exception) -> AIServiceError:
        """Keep only safe fields: HTTP code, Google's status label and a sanitised message.

        Never uses the exception's details, response, request or headers.
        """
        from google.genai import errors as genai_errors

        if isinstance(exc, genai_errors.APIError):
            code = exc.code if isinstance(exc.code, int) else None
            status = sanitise_error_message(exc.status, self._settings.api_key) if exc.status else "UNKNOWN"
            text = sanitise_error_message(exc.message, self._settings.api_key)
            timed_out = code in _TIMEOUT_STATUS_CODES or status == "DEADLINE_EXCEEDED"
            return AIServiceError(
                f"The AI service returned HTTP {code} {status}: {text}",
                timed_out=timed_out,
                status_code=code,
            )
        if _is_timeout(exc):
            return AIServiceError("The AI service timed out.", timed_out=True)
        # Network and other errors: only the exception type, never its text.
        return AIServiceError(f"The AI service call failed ({type(exc).__name__}).")


def build_http_options(settings: GeminiSettings, httpx_client: Optional[Any] = None) -> Any:
    """Per-attempt timeout plus bounded SDK retries for transient errors."""
    from google.genai import types

    return types.HttpOptions(
        timeout=int(settings.timeout_seconds * 1000),
        retry_options=types.HttpRetryOptions(
            attempts=RETRY_ATTEMPTS,
            initial_delay=RETRY_INITIAL_DELAY_SECONDS,
            max_delay=RETRY_MAX_DELAY_SECONDS,
            http_status_codes=RETRY_STATUS_CODES,
        ),
        httpx_client=httpx_client,
    )


def _is_timeout(exc: BaseException) -> bool:
    current: Optional[BaseException] = exc
    while current is not None:
        if isinstance(current, TimeoutError) or "timeout" in type(current).__name__.lower():
            return True
        current = current.__cause__ or current.__context__
    return False
