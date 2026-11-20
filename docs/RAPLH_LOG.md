# RAPLH Log

Status: five genuine iterations recorded so far. Only genuine iterations will be added here, each labelled as genuine or illustrative. No illustrative entries are used.

Each entry records: task/expectation, summary of the prompt given to the AI tool, files changed, test run and result, what was corrected, and the approval decision.

## Entries

### Iteration 1: Phase 1, repository scaffolding (GENUINE record)

- **Task / expectation**: Create the project structure and minimal placeholder files only, with no application code. Add dependencies (google-genai, pydantic, python-dotenv, pytest), a `.gitignore` that excludes secrets and runtime files, and a `.env.example` with placeholder names. Do not write the Working Style answers, do not invent RAPLH records, do not commit or push.
- **Prompt / instruction summary** (paraphrased, not the exact text): I asked Claude Code to act as a senior Python AI engineer, read both RAHN documents first, inspect the repo and Git status, propose and create the folder structure, create placeholders only, and report the tree, module responsibilities, files changed, issues and confirmation that no secrets were added. It was to stop after Phase 1 and wait for my approval.
- **What happened**:
  - The repo contained only `README.md` and one initial commit.
  - The assessment and Playbook PDFs were found in my Downloads folder.
  - The built-in PDF reader failed because `pdftoppm` is not installed, so the tool switched to `pdftotext`.
  - I interrupted the first attempt to read the Playbook. I then sent `/yolo`, which is not an installed command, so it was treated as a plain "go ahead". The tool re-read the Playbook with narrower commands.
  - The tool then created the folders and files.
- **Files changed**: created `.gitignore`, `.env.example`, `requirements.txt`, `main.py`, `data/fitdesk_data.json` (placeholder `{}`), `docs/SRS.md`, `docs/REGRESSION_TESTS.md`, `docs/RAPLH_LOG.md`, `fitdesk/` (`__init__.py`, `cli.py`, `models.py`, `gemini_client.py`, `knowledge_base.py`, `response_builder.py`, `approval.py`, `audit_log.py`), `tests/` (`conftest.py`, `test_agent.py`, `test_knowledge_base.py`). Modified `README.md` (empty section headings; Working style left for me).
- **Test run and result**: **No tests were run.** Phase 1 only created scaffolding and the test files contain only docstrings. Non-test checks were run: `git status`, a file listing, `git check-ignore` for the `.gitignore` rules, and a search for key-like strings. These are checks, not test results.
- **What was corrected**: Nothing in the code needed correcting. The only process correction was the PDF-reading fallback above. Issues raised and still open: the README title uses `sima-nyamfu` while the CV says "Simamkele Nyamfu" (repo name to be decided), `GEMINI_MODEL` is a placeholder, and the dependencies are unpinned.
- **Loop attempts**: one pass, no retries.
- **Approval decision**: I reviewed the Phase 1 report and approved it. Nothing was committed or pushed.

### Iteration 2: Phase 2, requirements and data preparation (GENUINE record)

- **Task / expectation**: Write `docs/SRS.md` (maximum two pages, traceable to the assessment), populate `data/fitdesk_data.json` with only the six approved facts, add the Phase 1 entry to this log, and review the result. No application code, no dependency installs, no commit or push.
- **Prompt / instruction summary** (paraphrased, not the exact text): I asked Claude Code to act as a senior AI engineer and software architect, re-read both RAHN documents, and complete Phase 2 only. That meant an SRS with the required sections, FR-01 onwards, NFR-01 to NFR-03, acceptance criteria and at least two ambiguities with assumptions. It also meant a clean JSON schema using only the six facts, a Phase 1 entry in this log with no invented test results, and a review of the SRS, JSON and escalation sentence. It was not to write my Working Style answers, and was to stop for approval before Phase 3.
- **What happened**:
  - The tool re-read both PDFs with `pdftotext`.
  - It wrote `docs/SRS.md` with a source tag (assessment or Playbook section) on each requirement.
  - It populated `data/fitdesk_data.json` with `packages` and `saturday_availability`, and added `id` fields and integer `price_zar` values.
  - It added Iteration 1 to this log and updated the status line.
  - It then ran review checks:
    - parsed the JSON and compared it to the six facts and the key names;
    - searched the SRS for the escalation phrase;
    - counted the SRS words (about 1,010);
    - listed the FR and NFR IDs;
    - ran `git status`.
- **Files changed**: created `docs/SRS.md` and `data/fitdesk_data.json` (replacing the `{}` placeholder); modified `docs/RAPLH_LOG.md` (Iteration 1 added, status line updated).
- **Test run and result**: **No application tests were run.** No application code exists yet and the test files are still empty placeholders. The review checks above are checks of documents and data, not test results. The JSON check found valid JSON, all six facts and no extra keys. The escalation phrase was found once in the SRS and matched the assessment text.
- **What was corrected**: Nothing was corrected during this iteration. The SRS page count could not be confirmed at that point, only its word count, and the tool said so in its report.
- **Follow-up after my review**: I returned Phase 2 for corrections: add this entry, verify the SRS page count, and use `rahn-assessment-simamkele-nyamfu` as the repository name in the README. The SRS was rendered to PDF with Microsoft Edge headless (A4, 2.54 cm margins, Calibri 11 pt, using a throwaway Markdown-to-HTML script kept outside the repo) and came to 2 pages, with page 2 nearly full. The remote GitHub repository was not renamed or modified.
- **Loop attempts**: one pass, no retries.
- **Approval decision**: Phase 2 was first returned for corrections (above), then approved. When approving it, I confirmed that the repository name `rahn-assessment-sima-nyamfu` is intentional and must not be renamed. This replaces the earlier `simamkele` instruction.

### Iteration 3: Phase 3, CLI enquiry assistant (GENUINE record)

- **Task / expectation**: Implement the CLI assistant to match the SRS and the brief, using the existing module layout. Gemini does structured classification, Pydantic validates it, and facts come only from `data/fitdesk_data.json`. Use the exact escalation sentence, require y/n approval before "sent", and handle invalid JSON, API failures and timeouts safely. Keep `status_log.json` local. No UI, WhatsApp, payments or bookings. Do not write the Working Style answers, do not commit or push, and do not change the SRS unless there is a real contradiction.
- **Prompt / instruction summary** (paraphrased): I told Claude Code that Phase 2 was approved and the repo name is intentional, and asked it to begin Phase 3 only. It was to follow RAPLH, run checks, record genuine work and test results, and stop for my review before Phase 4.
- **What happened (R, A, P)**:
  - The tool re-read the assessment and Playbook PDFs with `pdftotext`.
  - It found that `fitdesk/models.py` and `fitdesk/knowledge_base.py` already contained code in the Phase 2 commit, although the README and this log described every module as a placeholder. It kept and built on that code, and reported the mismatch.
  - It checked the installed `google-genai` 3.6.1 API (timeout option, error classes, `response_json_schema`) before writing the client.
  - Risks it planned for: AI text leaking into the reply, an AI value of `requires_human_approval: false`, timeouts raised by the HTTP library instead of the SDK, and a corrupt existing log being overwritten.
- **Design decisions**:
  - Gemini only labels the enquiry. The draft is built only from `KnowledgeBase` objects, so no AI text reaches it.
  - Staff approval is always asked for, whatever the AI says.
  - Every SDK error, including timeouts, is wrapped as `AIServiceError`. Only the exception type is shown, so no key or request detail reaches the log.
  - The log is a JSON array written through a temporary file. A corrupt log is left unchanged and the run is stopped.
- **Files changed**:
  - Implemented: `fitdesk/response_builder.py`, `fitdesk/approval.py`, `fitdesk/audit_log.py`, `fitdesk/gemini_client.py`, `fitdesk/cli.py`, `main.py`.
  - Modified: `fitdesk/models.py` (added the `ai_requires_human_approval` audit field).
  - Tests: `tests/conftest.py`, `tests/test_agent.py`, `tests/test_knowledge_base.py`.
  - Created: `pytest.ini`.
  - Modified: `.gitignore` (added `status_log.json.tmp`), `docs/REGRESSION_TESTS.md`, `docs/RAPLH_LOG.md`, `README.md`.
  - Not changed: `docs/SRS.md`, `data/fitdesk_data.json`.
- **Test runs and results (L)**:
  1. Attempt 1: `python -m pytest -q` failed at collection with `ModuleNotFoundError: No module named 'httpx'`. **Cause**: the tool assumed the SDK uses `httpx`, but `google-genai` 3.6.1 uses `httpx2`. **Fix**: the timeout test no longer imports `httpx`. It uses `TimeoutError`, a local `ReadTimeout`, and the real `httpx2.ReadTimeout` when installed. I also added `pytest.ini` (`pythonpath = .`) so that plain `pytest` can import the package.
  2. Attempt 2: 51 passed, 1 failed (`test_general_price_question_lists_all_packages`: got `'R180,'` instead of `'R180'`). **Cause**: a bug in the test, not the code. The price regex `R\d[\d,]*` also matched the list comma. **Fix**: the regex is now `R\d{1,3}(?:,\d{3})*`.
  3. Attempt 3: **52 passed, 0 failed.** No fix was attempted twice, so the "same fix fails twice" stop rule was not triggered.
  4. Manual checks of `python main.py`:
     - With no key: clear setup error, exit code 2, no log.
     - With a real SDK call through a dead local proxy: `ai_error` logged, exit code 1, no "sent".
     - With a piped interactive run: the invalid answer repeated the prompt and `y` recorded "sent".
     - The smoke-run `status_log.json` was deleted afterwards. `git check-ignore` confirms it is ignored.
- **What was corrected**: the two test problems above.
- **Not done / open**:
  - No live Gemini call with a real key has been made yet.
  - `GEMINI_MODEL` still has no chosen value.
  - Dependencies are still unpinned.
- **SRS**: no contradiction found, so it was not modified. One clarification for Phase 4, if wanted: the program exits with code 1 after an AI failure and code 2 for setup errors. The SRS says only "exits cleanly", and this is consistent with it.
- **Loop attempts**: 3 test runs (2 failures with different causes, each fixed once).
- **Approval decision**: I reviewed Phase 3. I then ran the app myself with my real key, got `ai_error (ServerError)`, and opened Iteration 4. Nothing was committed or pushed.

### Iteration 4: Live Gemini `ServerError`: investigation and minimal correction (GENUINE record)

- **Task / expectation**: Find out why a live run logged only `ai_error (ServerError)`.
  - Then show the HTTP status safely, add bounded retries and handle Ctrl+C cleanly.
  - Never log a failed or cancelled call as "sent".
  - Keep the key private, do not change the SRS, do not commit.
  - Report the root cause before changing any files.
- **Prompt / instruction summary** (paraphrased): First prompt: investigate only (status code, `GEMINI_MODEL`, structured-output support, retries, Ctrl+C) and propose a fix. Second prompt: I approved the proposed fix, kept the default timeout at 30 s, and asked for tests, documentation and exact results.
- **Investigation (R, A)**:
  - `.env` was read without printing the key. `GEMINI_MODEL='gemini-3.8-flash'` was read correctly; the key is set and is not the placeholder.
  - The cause of the hidden details: `gemini_client.py` replaced every error with `type(exc).__name__`, which threw away the safe `code`, `status` and `message` fields of the SDK's `APIError`.
  - Diagnostic calls from a throwaway script outside the repo, one attempt each:
    - `models.get` succeeded;
    - plain text returned **503 UNAVAILABLE**, "This model is currently experiencing high demand";
    - the app's structured config returned **504 DEADLINE_EXCEEDED**;
    - `gemini-3.5-flash` also returned **504**.
  - The SDK sends the 30 s timeout to the server as `X-Server-Timeout`, so the overloaded model hit that deadline.
  - Root cause: **Google-side overload (503/504), not a fault in the app or its config.** Structured-output support could not be confirmed live, because even plain calls failed.
  - SDK source check: with no `retry_options`, the SDK makes one attempt. `HttpRetryOptions` supports bounded retries (attempts and status codes).
  - Ctrl+C during the call gave a full traceback, because `KeyboardInterrupt` is not an `Exception`.
- **Plan (P)**: make small changes to `gemini_client.py`, `cli.py` and `main.py`, then add tests and update the docs.
- **Files changed**:
  - `fitdesk/gemini_client.py`:
    - `AIServiceError.status_code`;
    - `sanitise_error_message` (one line, at most 200 characters, removes the configured key, Google-format keys and `key=` URL parameters);
    - `APIError` turned into `HTTP <code> <STATUS>: <message>`, never using details, response, request or headers;
    - `build_http_options` with `HttpRetryOptions(attempts=3, initial_delay=1, max_delay=8, http_status_codes=[429, 500, 502, 503, 504])`.
  - `fitdesk/cli.py`:
    - Ctrl+C during the AI call is logged as `ai_error`, reason `cancelled by staff (Ctrl+C) while waiting for the AI service`;
    - Ctrl+C anywhere else exits cleanly with code 130 and writes no new record.
  - `main.py`: catches Ctrl+C during start-up.
  - `tests/test_agent.py`: 15 new test cases.
  - `docs/REGRESSION_TESTS.md`, `docs/RAPLH_LOG.md`, `README.md`.
  - Not changed: `docs/SRS.md`, `data/fitdesk_data.json`.
- **Test runs and results (L)**:
  1. `python -m pytest -q`: **67 passed** on the first run (52 old, 15 new). No fixes were needed.
  2. One live run of `python main.py` with `n` piped in. It printed `The AI service returned HTTP 503 UNAVAILABLE: This model is currently experiencing high demand...`, took 35 s within the retry limit, exited with code 1, and logged `ai_error` with no draft and no "sent".
- **What was corrected**: the over-strict error hiding, the missing bounded retries, and the Ctrl+C traceback.
- **Still open**:
  - No successful live Gemini response yet, because Google is still returning 503/504. So the real model's JSON passing Pydantic, and structured output with `gemini-3.8-flash`, are not yet proven.
  - Ctrl+C pressed by hand during a live call was not tried; only the automated tests cover it.
- **Loop attempts**: 1 test run, 1 live run.
- **Approval decision**: pending my review. Nothing was committed or pushed.

### Iteration 5: Live verification succeeded (GENUINE record)

- **Task / expectation**: Prove the assistant end to end against the real Gemini API: structured output passes Pydantic, the draft uses only data-file facts, and the approval step records `sent`.
- **What I changed**: configuration only, in my local `.env`, which is git-ignored and not committed. I replaced the API key with a new key from a different Google account, because the HTTP 429 RESOURCE_EXHAUSTED error showed the free-tier quota on my old account was used up. I set `GEMINI_MODEL=gemini-3.5-flash-lite` (instead of `gemini-3.8-flash`, which kept returning 503/504) and `GEMINI_TIMEOUT_SECONDS=90` (instead of the 30 s default). No code was changed.
- **Runs (from `status_log.json`)**:
  - Three runs from 12:47 to 12:51 UTC each logged `ai_error`, and none was sent:
    - cancelled by staff (Ctrl+C) while waiting for the AI service;
    - HTTP 429 RESOURCE_EXHAUSTED;
    - HTTP 503 UNAVAILABLE.
  - **2026-11-20 14:54 SAST (12:54:26 UTC):** `py main.py "How much is the 12-session pack and do you have Saturday slots?"` succeeded.
    - The draft was `The 12 sessions package costs R1,680. Saturday slots available: 09:00, 11:00; full: 10:00.`
    - I answered `y`, and `sent` was logged with `approved: true` and intent `pricing_and_availability`.
- **Test result**: live manual check 5 in `docs/REGRESSION_TESTS.md`: **Pass**. Live structured output plus Pydantic validation is now proven on `gemini-3.5-flash-lite`.
- **Prompt / instruction summary** (paraphrased): I asked Claude Code to update the docs only (README, regression tests, this log and `.env.example`) to record the live success, with no code changes.
- **Files changed**: in the repo, only documentation:
  - `README.md` (status banner and "What doesn't work yet");
  - `docs/REGRESSION_TESTS.md` (manual check 5 and "Not yet verified");
  - `docs/RAPLH_LOG.md` (this entry);
  - `.env.example` (an optional `GEMINI_TIMEOUT_SECONDS=90` placeholder).

  `.env` changed locally but is not tracked. The code, SRS and data file were not changed.
- **Still open**:
  - No successful response from `gemini-3.8-flash` yet.
  - Ctrl+C pressed by hand during a live call is not yet confirmed.
- **Loop attempts**: 4 live runs (3 `ai_error`, 1 success), no code fixes.
- **Approval decision**: pending my review. Nothing was committed or pushed.

## Reflection questions

### 1. How would you stop an AI coding agent from changing unrelated files or exposing your API key?

- **Unrelated files:**
  - Every prompt names the phase and what is out of bounds (for example "do not modify the SRS", "do not rename the repo", "do not commit or push").
  - The agent must list every changed file at the end.
  - Before approving, I check `git status` and `git diff` against that list. Because nothing is committed until I approve, an unwanted change can simply be discarded.
- **API key:**
  - The key lives only in `.env`, which is in `.gitignore`. Only `.env.example`, with placeholder values, is committed.
  - The tests unset the key and block the network, so they never need it.
  - The agent may check that the key is set, but never print it. In Iteration 4 it reported only "set" and "not the placeholder", and the diagnostic script blanked out the key before printing anything.
  - Error messages are cleaned before they reach the console or `status_log.json`.
  - Before each commit, I scan the changed files for the key and confirm with `git check-ignore` that `.env` is ignored.

### 2. How would you stop the loop if the agent keeps repeating the same failed fix?

- **Set a limit before starting.** I set a maximum number of attempts at the start (three test runs in Phase 3).
- **Find the cause before retrying.** After each failure, the agent must read the error and name the cause before changing anything. In Iteration 3, the two failures had different causes (a wrong assumption about `httpx`, then a regex bug in a test), and each was fixed once.
- **Stop after two identical failures.** If the same fix fails twice, I stop the loop, as the Playbook says. I don't let the agent try a third variation. I would ask for a written diagnosis, check the facts myself, and escalate to a mentor if it is still unclear.
- **Investigate-only step.** For a problem outside the code, I ask for investigation only and a report before any file is changed. That is how the live Gemini error in Iteration 4 turned out to be Google-side overload (503/504) rather than a code bug.
- **Bound the program's own retries.** The app itself uses at most 3 attempts.
