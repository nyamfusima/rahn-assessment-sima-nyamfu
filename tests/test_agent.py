"""End-to-end flow tests with the Gemini response mocked (FR-01 to FR-06, NFR-01, NFR-02).

Each test ID matches docs/REGRESSION_TESTS.md.
"""

import json
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from fitdesk import cli
from fitdesk.audit_log import AuditLogError, append_record
from fitdesk.gemini_client import (
    AIServiceError,
    ConfigError,
    GeminiClassifier,
    GeminiSettings,
    load_settings,
)
from fitdesk.models import StatusRecord
from fitdesk.response_builder import ESCALATION_PHRASE
from tests.conftest import FakeClassifier, ScriptedInput, ai_json, read_log

BRIEF_EXAMPLE = "How much is the 12-session pack and do you have Saturday slots?"


def run(message, classifier, kb, log_path, *answers):
    scripted = ScriptedInput(*answers)
    output: list[str] = []
    code = cli.main(
        argv=[message],
        classifier=classifier,
        kb=kb,
        log_path=log_path,
        input_fn=scripted,
        output_fn=output.append,
    )
    return code, read_log(log_path), scripted, "\n".join(output)


def sent_count(records):
    return sum(1 for r in records if r["status"] == "sent")


# RT-01: normal enquiry answerable from the data, staff approve (y)
def test_rt01_normal_enquiry_approved_is_sent_once(kb, log_path):
    fake = FakeClassifier(ai_json("pricing_and_availability", packages=["12 sessions"], asks_saturday=True))
    code, records, scripted, output = run(BRIEF_EXAMPLE, fake, kb, log_path, "y")
    assert code == 0
    assert fake.calls == [BRIEF_EXAMPLE]
    assert scripted.prompts == ["Send? (y/n) "]
    assert "R1,680" in output
    assert len(records) == 1 and sent_count(records) == 1
    record = records[0]
    assert record["intent"] == "pricing_and_availability"
    assert record["approved"] is True and record["is_escalation"] is False
    assert "R1,680" in record["draft"]


# RT-02: something not in the data -> exact escalation phrase; n -> not sent
def test_rt02_missing_fact_escalates_and_is_not_sent_without_approval(kb, log_path):
    fake = FakeClassifier(ai_json("pricing", packages=["20 sessions"]))
    code, records, _, output = run("How much is a 20-session pack?", fake, kb, log_path, "n")
    assert code == 0
    assert records[0]["draft"] == ESCALATION_PHRASE
    assert records[0]["status"] == "escalation_not_approved"
    assert sent_count(records) == 0
    assert "escalation" in output


# RT-02b / AC-06: escalation message is recorded as sent only after y
def test_rt02b_escalation_sent_only_after_y(kb, log_path):
    fake = FakeClassifier(ai_json("saturday_availability", asks_saturday=True, times=["14:00"]))
    _, records, _, _ = run("Is Saturday 14:00 free?", fake, kb, log_path, "y")
    assert records[0]["draft"] == ESCALATION_PHRASE
    assert records[0]["status"] == "sent" and records[0]["is_escalation"] is True


# RT-03: broken JSON from the AI -> no draft, no prompt, no "sent"
@pytest.mark.parametrize(
    "raw",
    [
        "Sure! The 12-session pack is R1,680.",  # paragraph, not JSON
        '{"intent": "pricing", "details": ',  # truncated JSON
        "",  # empty
        None,  # no text at all
    ],
)
def test_rt03_invalid_json_is_never_sent(kb, log_path, raw):
    code, records, scripted, _ = run("How much?", FakeClassifier(raw), kb, log_path)
    assert code == cli.EXIT_AI_FAILURE
    assert scripted.prompts == []  # staff are never asked to approve
    assert len(records) == 1 and records[0]["status"] == "invalid_ai_output"
    assert records[0]["draft"] is None and sent_count(records) == 0


# RT-03b: valid JSON that does not match the Pydantic model
@pytest.mark.parametrize(
    "payload",
    [
        {"intent": "pricing", "details": {}},  # missing fields
        json.loads(ai_json(intent="booking")),  # intent not allowed
        {**json.loads(ai_json()), "requires_human_approval": "yes"},  # wrong type
        [1, 2, 3],  # not an object
    ],
)
def test_rt03b_schema_mismatch_is_never_sent(kb, log_path, payload):
    code, records, scripted, _ = run("How much?", FakeClassifier(json.dumps(payload)), kb, log_path)
    assert code == cli.EXIT_AI_FAILURE
    assert scripted.prompts == []
    assert records[0]["status"] == "invalid_ai_output" and sent_count(records) == 0


# RT-04: AI service fails or times out -> clean exit, failure recorded, no "sent"
@pytest.mark.parametrize("error", [AIServiceError("The AI service call failed (ServerError)."),
                                   AIServiceError("The AI service timed out.", timed_out=True)])
def test_rt04_ai_failure_is_handled_and_never_sent(kb, log_path, error):
    code, records, scripted, output = run("How much?", FakeClassifier(error=error), kb, log_path)
    assert code == cli.EXIT_AI_FAILURE
    assert scripted.prompts == []
    assert records[0]["status"] == "ai_error" and sent_count(records) == 0
    assert "Nothing was sent" in output


# RT-05: staff answer n on an answerable draft
def test_rt05_staff_say_n_is_not_sent(kb, log_path):
    fake = FakeClassifier(ai_json("pricing", packages=["12 sessions"]))
    _, records, _, _ = run("How much is the 12-session pack?", fake, kb, log_path, "n")
    assert records[0]["status"] == "rejected" and records[0]["approved"] is False
    assert sent_count(records) == 0


# RT-06: staff answer y (covered with RT-01); invalid answers repeat the prompt, never count as y
def test_rt06_invalid_answers_repeat_until_y(kb, log_path):
    fake = FakeClassifier(ai_json("pricing", packages=["5 sessions"]))
    _, records, scripted, _ = run("Price of 5 sessions?", fake, kb, log_path, "yes", "", "maybe", " Y ")
    assert len(scripted.prompts) == 4
    assert records[0]["status"] == "sent"


def test_end_of_input_at_prompt_is_not_approval(kb, log_path):
    def eof(prompt):
        raise EOFError

    code = cli.main(argv=["How much?"], classifier=FakeClassifier(ai_json("pricing", packages=["5 sessions"])),
                    kb=kb, log_path=log_path, input_fn=eof, output_fn=lambda s: None)
    assert code == 0
    assert read_log(log_path)[0]["status"] == "rejected"


def test_ai_saying_no_approval_needed_is_ignored(kb, log_path):
    fake = FakeClassifier(ai_json("pricing", packages=["12 sessions"], approval=False))
    _, records, scripted, _ = run("How much?", fake, kb, log_path, "n")
    assert scripted.prompts == ["Send? (y/n) "]
    assert records[0]["status"] == "rejected"
    assert records[0]["ai_requires_human_approval"] is False


def test_log_appends_one_record_per_enquiry(kb, log_path):
    fake = FakeClassifier(ai_json("pricing", packages=["12 sessions"]))
    run("first", fake, kb, log_path, "y")
    _, records, _, _ = run("second", fake, kb, log_path, "n")
    assert [r["status"] for r in records] == ["sent", "rejected"]


def test_message_typed_at_prompt_when_no_argument(kb, log_path):
    fake = FakeClassifier(ai_json("pricing", packages=["12 sessions"]))
    scripted = ScriptedInput("How much is the 12-session pack?", "y")
    cli.main(argv=[], classifier=fake, kb=kb, log_path=log_path, input_fn=scripted, output_fn=lambda s: None)
    assert fake.calls == ["How much is the 12-session pack?"]
    assert read_log(log_path)[0]["status"] == "sent"


def test_corrupt_existing_log_is_not_overwritten(kb, log_path):
    log_path.write_text("not json", encoding="utf-8")
    fake = FakeClassifier(ai_json("pricing", packages=["12 sessions"]))
    code = cli.main(argv=["How much?"], classifier=fake, kb=kb, log_path=log_path,
                    input_fn=ScriptedInput("y"), output_fn=lambda s: None)
    assert code == cli.EXIT_SETUP_ERROR
    assert log_path.read_text(encoding="utf-8") == "not json"


def test_status_record_refuses_sent_without_approval():
    with pytest.raises(ValidationError):
        StatusRecord(timestamp="2026-11-20T10:00:00Z", customer_message="x", draft="d", status="sent", approved=False)


def test_append_record_rejects_non_list_log(log_path):
    log_path.write_text("{}", encoding="utf-8")
    record = StatusRecord(timestamp="2026-11-20T10:00:00Z", customer_message="x", status="ai_error")
    with pytest.raises(AuditLogError):
        append_record(record, log_path)


# --- Gemini client (mocked SDK client; no network, no key) -----------------------------------

SETTINGS = GeminiSettings(api_key="test-key-not-real", model="test-model", timeout_seconds=5)


class FakeModels:
    def __init__(self, result=None, error=None):
        self.result, self.error, self.kwargs = result, error, None

    def generate_content(self, **kwargs):
        self.kwargs = kwargs
        if self.error:
            raise self.error
        return self.result


def test_gemini_client_requests_structured_json():
    models = FakeModels(result=SimpleNamespace(text=ai_json()))
    classifier = GeminiClassifier(SETTINGS, ["12 sessions"], client=SimpleNamespace(models=models))
    assert classifier.classify("hi") == ai_json()
    config = models.kwargs["config"]
    assert models.kwargs["model"] == "test-model"
    assert config.response_mime_type == "application/json"
    assert config.response_json_schema["required"] == ["intent", "details", "requires_human_approval"]


class ReadTimeout(Exception):
    """Same class name as the SDK transport's timeout (httpx/httpx2 ReadTimeout)."""


def _timeout_errors():
    errors = [TimeoutError("timed out"), ReadTimeout("timed out")]
    try:  # the transport library google-genai 3.x actually uses, when installed
        import httpx2

        errors.append(httpx2.ReadTimeout("timed out"))
    except ImportError:
        pass
    return errors


@pytest.mark.parametrize("error", _timeout_errors(), ids=lambda e: type(e).__module__ + "." + type(e).__name__)
def test_gemini_client_wraps_timeout(error):
    models = FakeModels(error=error)
    classifier = GeminiClassifier(SETTINGS, [], client=SimpleNamespace(models=models))
    with pytest.raises(AIServiceError) as info:
        classifier.classify("hi")
    assert info.value.timed_out is True


def test_gemini_client_wraps_other_errors_without_leaking_details():
    models = FakeModels(error=RuntimeError("secret test-key-not-real in message"))
    classifier = GeminiClassifier(SETTINGS, [], client=SimpleNamespace(models=models))
    with pytest.raises(AIServiceError) as info:
        classifier.classify("hi")
    assert info.value.timed_out is False
    assert "test-key-not-real" not in str(info.value)


def test_missing_api_key_is_a_setup_error_with_no_log(kb, log_path, monkeypatch):
    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **k: False)
    output: list[str] = []
    code = cli.main(argv=["How much?"], kb=kb, log_path=log_path, input_fn=ScriptedInput(), output_fn=output.append)
    assert code == cli.EXIT_SETUP_ERROR
    assert "GEMINI_API_KEY" in "\n".join(output)
    assert not log_path.exists()


def test_placeholder_values_from_env_example_are_rejected(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "your_api_key_here")
    monkeypatch.setenv("GEMINI_MODEL", "some-model")
    with pytest.raises(ConfigError):
        load_settings()


# --- Live-error handling: HTTP status, sanitising, bounded retries, Ctrl+C (Iteration 4) ------

from google.genai import errors as genai_errors

from fitdesk.gemini_client import (
    RETRY_ATTEMPTS,
    RETRY_STATUS_CODES,
    build_http_options,
    sanitise_error_message,
)

FAKE_GOOGLE_KEY = "AIzaSyA1234567890abcdefghijklmnopqrstu"  # format only, not a real key


def google_error(cls, code, status, message):
    body = {"error": {"code": code, "status": status, "message": message,
                      "details": [{"reason": "DETAIL_THAT_MUST_NOT_SHOW"}]}}
    return cls(code, body)


# RT-07: the real HTTP status reaches staff and the log, with no key and no details
@pytest.mark.parametrize(
    "cls, code, status, timed_out",
    [
        (genai_errors.ServerError, 503, "UNAVAILABLE", False),
        (genai_errors.ServerError, 504, "DEADLINE_EXCEEDED", True),
        (genai_errors.ServerError, 500, "INTERNAL", False),
        (genai_errors.ClientError, 429, "RESOURCE_EXHAUSTED", False),
        (genai_errors.ClientError, 403, "PERMISSION_DENIED", False),
        (genai_errors.ClientError, 404, "NOT_FOUND", False),
    ],
)
def test_rt07_api_error_shows_status_without_secrets(cls, code, status, timed_out):
    message = (f"Model busy.\n  key {SETTINGS.api_key} in "
               f"https://example.test/v1?key={SETTINGS.api_key}&alt=json also {FAKE_GOOGLE_KEY}")
    models = FakeModels(error=google_error(cls, code, status, message))
    classifier = GeminiClassifier(SETTINGS, [], client=SimpleNamespace(models=models))
    with pytest.raises(AIServiceError) as info:
        classifier.classify("hi")
    text = str(info.value)
    assert text.startswith(f"The AI service returned HTTP {code} {status}: Model busy.")
    assert SETTINGS.api_key not in text and FAKE_GOOGLE_KEY not in text
    assert "DETAIL_THAT_MUST_NOT_SHOW" not in text and "\n" not in text
    assert info.value.status_code == code and info.value.timed_out is timed_out


def test_rt07_status_reaches_log_and_is_not_sent(kb, log_path):
    error = AIServiceError("The AI service returned HTTP 503 UNAVAILABLE: busy", status_code=503)
    code, records, scripted, output = run("How much?", FakeClassifier(error=error), kb, log_path)
    assert code == cli.EXIT_AI_FAILURE and scripted.prompts == []
    assert "HTTP 503 UNAVAILABLE" in output and "HTTP 503 UNAVAILABLE" in records[0]["reason"]
    assert records[0]["status"] == "ai_error" and sent_count(records) == 0


def test_sanitised_message_is_short_and_single_line():
    cleaned = sanitise_error_message("word " * 200 + "\n\nend")
    assert len(cleaned) <= 200 and "\n" not in cleaned and cleaned.endswith("...")
    assert sanitise_error_message(None) == "no message"


# RT-08: bounded retries via the SDK's HttpRetryOptions
def test_rt08_http_options_have_bounded_retries_for_transient_errors_only():
    options = build_http_options(SETTINGS)
    assert options.timeout == 5000  # SETTINGS.timeout_seconds = 5, per attempt
    retry = options.retry_options
    assert retry.attempts == RETRY_ATTEMPTS == 3
    assert set(retry.http_status_codes) == {429, 500, 502, 503, 504}
    assert not {400, 401, 403, 404} & set(retry.http_status_codes)
    assert retry.max_delay == 8.0


httpx2 = pytest.importorskip("httpx2")


def sdk_classifier_with_fake_server(monkeypatch, codes):
    """Real google-genai client and retry logic; the HTTP server is faked (no network)."""
    from google import genai

    calls = []

    def handler(request):
        calls.append(request)
        code = codes[min(len(calls), len(codes)) - 1]
        if code == 200:
            return httpx2.Response(200, json={"candidates": [{"content": {"role": "model", "parts": [{"text": ai_json()}]}}]})
        return httpx2.Response(code, json={"error": {"code": code, "status": "UNAVAILABLE", "message": "high demand"}})

    monkeypatch.setattr("tenacity.nap.time.sleep", lambda seconds: None)  # skip back-off waits
    client = genai.Client(
        api_key=SETTINGS.api_key,
        http_options=build_http_options(SETTINGS, httpx_client=httpx2.Client(transport=httpx2.MockTransport(handler))),
    )
    return GeminiClassifier(SETTINGS, ["12 sessions"], client=client), calls


def test_rt08_persistent_503_stops_after_three_attempts(monkeypatch):
    classifier, calls = sdk_classifier_with_fake_server(monkeypatch, [503])
    with pytest.raises(AIServiceError) as info:
        classifier.classify("hi")
    assert len(calls) == 3
    assert info.value.status_code == 503
    assert "HTTP 503 UNAVAILABLE: high demand" in str(info.value)


def test_rt08_transient_503_then_success_returns_json(monkeypatch):
    classifier, calls = sdk_classifier_with_fake_server(monkeypatch, [503, 200])
    assert classifier.classify("hi") == ai_json()
    assert len(calls) == 2


def test_rt08_permanent_404_is_not_retried(monkeypatch):
    classifier, calls = sdk_classifier_with_fake_server(monkeypatch, [404])
    with pytest.raises(AIServiceError) as info:
        classifier.classify("hi")
    assert len(calls) == 1 and info.value.status_code == 404


# RT-09: Ctrl+C handled cleanly; never "sent"
def test_rt09_ctrl_c_during_ai_call_is_logged_as_not_sent(kb, log_path):
    code, records, scripted, output = run("How much?", FakeClassifier(error=KeyboardInterrupt()), kb, log_path)
    assert code == cli.EXIT_CANCELLED
    assert scripted.prompts == []
    assert records[0]["status"] == "ai_error" and records[0]["reason"] == cli.CANCELLED_REASON
    assert sent_count(records) == 0
    assert "Nothing was sent" in output


def test_rt09_ctrl_c_at_approval_prompt_is_not_approval(kb, log_path):
    def interrupt(prompt):
        raise KeyboardInterrupt

    fake = FakeClassifier(ai_json("pricing", packages=["12 sessions"]))
    code = cli.main(argv=["How much?"], classifier=fake, kb=kb, log_path=log_path,
                    input_fn=interrupt, output_fn=lambda s: None)
    assert code == 0
    assert read_log(log_path)[0]["status"] == "rejected"


def test_rt09_ctrl_c_anywhere_else_exits_cleanly_without_a_record(kb, log_path, monkeypatch):
    def interrupt(*args, **kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(cli, "append_record", interrupt)
    output: list[str] = []
    fake = FakeClassifier(ai_json("pricing", packages=["12 sessions"]))
    code = cli.main(argv=["How much?"], classifier=fake, kb=kb, log_path=log_path,
                    input_fn=ScriptedInput("y"), output_fn=output.append)
    assert code == cli.EXIT_CANCELLED
    assert "Cancelled" in "\n".join(output)
    assert not log_path.exists()
