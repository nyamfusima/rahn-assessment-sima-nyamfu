# Regression Tests

Status: automated tests written and run in Phase 3, then extended in Iteration 4 (live-error handling). All results below are from real runs on 2026-11-20 (Windows 11, Python 3.13.13, pytest 9.2.0, `google-genai` 3.6.1, in `.venv`).

Command: `python -m pytest -v`. Latest result: **67 passed, 0 failed, 0 skipped** (67 items, counting parametrised cases). This is 52 from Phase 3 plus 15 from Iteration 4.

How the tests run: Gemini is replaced by a fake classifier (or a fake SDK client) that returns canned text or raises a canned error. An autouse fixture in `tests/conftest.py` unsets `GEMINI_API_KEY`, `GEMINI_MODEL` and `GEMINI_TIMEOUT_SECONDS` and blocks all socket connections. The tests therefore prove AC-07: no key, no network, no paid calls. Each test writes its log to a temporary folder, never to the real `status_log.json`.

| ID | Requirement | Input / precondition | Steps | Expected result | Actual result | Pass/fail |
|---|---|---|---|---|---|---|
| RT-01 | FR-01–FR-06, AC-01, AC-05 | Message: "How much is the 12-session pack and do you have Saturday slots?"; mocked AI JSON: intent `pricing_and_availability`, packages `["12 sessions"]`, Saturday asked | Run `cli.main`; staff answer `y` | Draft contains R1,680 and the three Saturday slots from the data; prompt shown once; exactly one `sent` record | As expected | Pass (automated: `test_rt01_normal_enquiry_approved_is_sent_once`) |
| RT-02 | FR-04, AC-02, AC-06 | Message about a 20-session pack; mocked AI JSON: packages `["20 sessions"]` | Run; staff answer `n` | Draft is exactly `I'll check with the owner and come back to you.`; status `escalation_not_approved`; no `sent` | As expected | Pass (automated: `test_rt02_missing_fact_escalates_and_is_not_sent_without_approval`) |
| RT-02b | FR-04, FR-06, AC-06 | Mocked AI JSON: Saturday time `14:00` (not in data) | Run; staff answer `y` | Draft is exactly the escalation phrase; recorded `sent` with `is_escalation: true` only because staff approved | As expected | Pass (automated: `test_rt02b_escalation_sent_only_after_y`) |
| RT-03 | FR-02, NFR-02, AC-03 | Mocked AI text: a plain paragraph, truncated JSON, empty string, `None` (4 cases) | Run | No draft, approval prompt never shown, status `invalid_ai_output`, no `sent`, exit code 1 | As expected (4/4) | Pass (automated: `test_rt03_invalid_json_is_never_sent`) |
| RT-03b | FR-02, NFR-02, AC-03 | Valid JSON that fails the Pydantic model: missing fields, intent `booking`, `"requires_human_approval": "yes"`, a JSON list (4 cases) | Run | Same as RT-03 | As expected (4/4) | Pass (automated: `test_rt03b_schema_mismatch_is_never_sent`) |
| RT-04 | NFR-02, AC-04 | Fake classifier raises `AIServiceError` for a failure and for a timeout (2 cases) | Run | No crash, no prompt, status `ai_error`, "Nothing was sent" printed, no `sent`, exit code 1 | As expected (2/2) | Pass (automated: `test_rt04_ai_failure_is_handled_and_never_sent`) |
| RT-04b | NFR-02, NFR-01 | Fake SDK client raises `TimeoutError`, a `ReadTimeout`, the real `httpx2.ReadTimeout`, and a `RuntimeError` whose message contains a fake key | Call `GeminiClassifier.classify` | Timeouts become `AIServiceError(timed_out=True)`; other errors become `AIServiceError` whose text does not contain the key | As expected (4/4) | Pass (automated: `test_gemini_client_wraps_timeout`, `test_gemini_client_wraps_other_errors_without_leaking_details`) |
| RT-05 | FR-05, FR-06, AC-05 | Mocked AI JSON for the 12-session pack | Run; staff answer `n` | Status `rejected`, `approved: false`, no `sent` | As expected | Pass (automated: `test_rt05_staff_say_n_is_not_sent`) |
| RT-06 | FR-05, FR-06, SRS section 7 | Mocked AI JSON for the 5-session pack | Run; staff answer `yes`, empty, `maybe`, then ` Y ` | Prompt repeats for the 3 invalid answers (never treated as y); `Y` with spaces is accepted; one `sent` record | As expected | Pass (automated: `test_rt06_invalid_answers_repeat_until_y`) |
| RT-07 | NFR-01, NFR-02 | Fake SDK client raises a real `google.genai` `ServerError` or `ClientError` for HTTP 503, 504, 500, 429, 403 and 404 (6 cases). The error message contains the configured key, a `?key=` URL and a Google-format key, plus a `details` entry | Call `GeminiClassifier.classify` | Message is `The AI service returned HTTP <code> <STATUS>: <message>` on one line. No key, no `details`. `status_code` is set. Only 504 counts as a timeout. The same text reaches the console and the log, with status `ai_error` and no `sent` | As expected (6/6, plus the log check) | Pass (automated: `test_rt07_api_error_shows_status_without_secrets`, `test_rt07_status_reaches_log_and_is_not_sent`, `test_sanitised_message_is_short_and_single_line`) |
| RT-08 | NFR-02 | Real `google-genai` client and its retry logic, with the HTTP server faked by `httpx2.MockTransport` (no network). Back-off sleeps are skipped | Server always returns 503; returns 503 then 200; returns 404 | Always 503: exactly **3** requests, then `AIServiceError` with 503. 503 then 200: 2 requests, valid JSON returned. 404: **1** request (not retried). The retry settings allow only 429/500/502/503/504 | As expected | Pass (automated: `test_rt08_*`, 4 tests) |
| RT-09 | FR-06, Rule 2 | Ctrl+C (`KeyboardInterrupt`) during the AI call, at the approval prompt, and while writing the log | Run `cli.main` | No traceback. During the AI call: "Nothing was sent", `ai_error` with reason `cancelled by staff (Ctrl+C) while waiting for the AI service`, exit code 130. At the prompt: `rejected`. While writing the log: "Cancelled", no record written, exit code 130. Never `sent` | As expected | Pass (automated: `test_rt09_*`, 3 tests) |

## Additional automated checks (same run, all passed)

- **AC-01**: `test_ac01_twelve_session_price_only`: the draft contains R1,680 and no other price.
- **AC-02**: `test_ac02_unknown_package_is_exact_escalation`, `test_ac02_unknown_saturday_time_is_exact_escalation`, `test_other_intent_is_exact_escalation`.
- **SRS Q1** (partly answerable): `test_partly_answerable_enquiry_states_facts_then_escalates`: the known fact is stated, then the exact escalation phrase follows.
- **Rule 1** (no invented data): `test_ai_labels_are_never_copied_into_the_draft`: an AI label "12 sessions for R99" does not put R99 in the draft.
- **Rule 2** (human in the loop): `test_ai_saying_no_approval_needed_is_ignored`: AI `requires_human_approval: false` still triggers the prompt. `test_end_of_input_at_prompt_is_not_approval`: end of input is treated as not approved.
- **Log safety**: `test_corrupt_existing_log_is_not_overwritten`, `test_append_record_rejects_non_list_log`, `test_status_record_refuses_sent_without_approval`, `test_log_appends_one_record_per_enquiry`.
- **Setup**: `test_missing_api_key_is_a_setup_error_with_no_log`, `test_placeholder_values_from_env_example_are_rejected`, `test_gemini_client_requests_structured_json` (JSON MIME type and schema are sent to Gemini).
- **Data**: `test_data_file_has_exactly_the_approved_facts`, package and time matching, and errors for a missing or malformed data file.

## Manual checks of the real program (not automated)

1. `python main.py "How much is the 12-session pack?"` with no `.env`: printed `Setup error: GEMINI_API_KEY is not set...`, exit code 2, no log written. **Pass.**
2. A real SDK call with a fake key, routed to a dead local proxy (`HTTPS_PROXY=http://127.0.0.1:9`) so nothing left the machine: printed `AI service problem: The AI service call failed (ConnectError). Nothing was sent.`, exit code 1, one `ai_error` record in `status_log.json`. **Pass.** (That log file was then deleted.)
3. Interactive run through the real `input()` prompt with stdin piped and a fake classifier: the invalid answer `maybe` repeated the prompt, `y` recorded `sent`. **Pass.**

4. **Live Gemini runs with a real key (Iteration 4, 2026-11-20).** `.env` sets `GEMINI_MODEL=gemini-3.8-flash`.
   - Before the fix: two runs of the app logged only `ai_error (ServerError)`.
   - Single-attempt diagnostic calls (a throwaway script outside the repo) found:
     - `models.get` succeeded: the model exists and supports `generateContent`;
     - `generate_content` returned **503 UNAVAILABLE** ("This model is currently experiencing high demand") without the schema;
     - with the app's structured config it returned **504 DEADLINE_EXCEEDED** (twice);
     - `gemini-3.5-flash` also returned **504**.
   - After the fix, one run of `python main.py "How much is the 12-session pack and do you have Saturday slots?"` (with `n` piped to the prompt) printed `The AI service returned HTTP 503 UNAVAILABLE: This model is currently experiencing high demand...`. It took 35 s within the 3-attempt limit, exited with code 1, and logged `ai_error` with no draft and no `sent`. **Pass for error handling.**

5. **Live end-to-end success (2026-11-20, 14:54 SAST = 12:54 UTC).** `.env` set `GEMINI_MODEL=gemini-3.5-flash-lite` and `GEMINI_TIMEOUT_SECONDS=90`. These were configuration changes only; the code was not changed.
   - **Command:** `py main.py "How much is the 12-session pack and do you have Saturday slots?"`
   - **Result:** Gemini returned structured JSON, which passed the Pydantic model. The printed draft was `The 12 sessions package costs R1,680. Saturday slots available: 09:00, 11:00; full: 10:00.` All of it comes from the data file.
   - **Approval:** staff answered `y`, and `status_log.json` recorded `sent` with `approved: true` and intent `pricing_and_availability` at 12:54:26 UTC.
   - **Earlier runs:** the three runs just before it, from 12:47 to 12:51 UTC, each logged `ai_error`. In order: cancelled by staff (Ctrl+C) while waiting for the AI service, HTTP 429 RESOURCE_EXHAUSTED, and HTTP 503 UNAVAILABLE. None was `sent`.

   **Pass.** Requirements covered: FR-01 to FR-06, AC-01 and AC-05 (live).

**Not yet verified:**
- **A successful live response from `gemini-3.8-flash`.** Every live call to that model on 2026-11-20 returned 503 or 504.
- **Ctrl+C pressed by hand during a live call.** This is covered only by the automated tests, which raise `KeyboardInterrupt` directly.
