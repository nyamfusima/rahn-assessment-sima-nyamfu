# RAPLH Log

Status: two genuine iterations recorded so far. Only genuine iterations will be added here, each labelled as genuine or illustrative. No illustrative entries are used.

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
- **Approval decision**: pending. Phase 2 was returned for corrections and has not yet been approved. Nothing was committed or pushed.

## Reflection questions (to be answered at the end)

1. How would you stop an AI coding agent from changing unrelated files or exposing your API key?
2. How would you stop the loop if the agent keeps repeating the same failed fix?
