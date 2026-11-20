# RAHN FitDesk Enquiry Assistant

**Hours spent: 4**

> **Project status: Phase 3 built, awaiting review.** The command-line assistant is implemented and 67 automated tests pass with Gemini mocked. **A live end-to-end run succeeded** on 2026-11-20 with `gemini-3.5-flash-lite` and `GEMINI_TIMEOUT_SECONDS=90`. It produced a valid structured draft, staff answered `y`, and `sent` was logged. `gemini-3.8-flash` still returned HTTP 503/504 that day. See [What doesn't work yet](#what-doesnt-work-yet).

## Project overview

A small fitness studio in Hermanus gets repeated enquiries about session packages and Saturday availability. This project is a deliberately small, command-line version of the "FitDesk" enquiry assistant, built for the RAHN January 2027 Agentic AI internship assessment.

**Business objective:** let staff answer package-price and Saturday-availability enquiries faster, using only approved data, while keeping a human in control. Nothing may be recorded as sent without staff approval, and the assistant must never invent prices or availability.

Out of scope (per the brief): WhatsApp or any messaging integration, bookings, payments, calendars and any web UI. In this project, "sent" is only a status in a local log; nothing is delivered to a customer.

## Features and scope

**Behaviour** (see `docs/SRS.md` for the numbered requirements):

1. Read one customer message typed at the command line.
2. Send it to the Gemini API and receive structured JSON (`intent`, `details`, `requires_human_approval`), validated with a Pydantic model.
3. Look up facts only in `data/fitdesk_data.json`.
4. Draft a reply from those facts only. If the answer is not in the data, the reply must be exactly: `I'll check with the owner and come back to you.`
5. Print the draft and ask `Send? (y/n)`.
6. Record the outcome in a local `status_log.json`. A "sent" status is never recorded when staff answer `n`, the AI returns invalid JSON, the AI call fails or times out, or the reply is an escalation that staff did not approve.

**Implemented and tested so far:** all six steps, with Gemini mocked in the automated tests (see `docs/REGRESSION_TESTS.md`).

How the safety rules are enforced:

- Gemini only **labels** the enquiry (which packages, which Saturday times, anything else asked). The reply is built only from the data file, so no text written by the AI ever appears in it.
- Anything not found in the data adds the exact escalation sentence. If nothing can be answered, the draft is exactly that sentence.
- The `Send? (y/n)` prompt is always shown for a valid draft, even if the AI says approval is not needed. Only `y` or `n` are accepted (case and surrounding spaces are ignored); anything else repeats the prompt, and end of input counts as "not approved".
- If the AI call fails or times out, or its output is invalid, no draft is built and staff are not asked. The failure is logged as `ai_error` or `invalid_ai_output`.
- API errors are shown and logged as `HTTP <code> <STATUS>: <message>`, for example `HTTP 503 UNAVAILABLE: This model is currently experiencing high demand...`. The message is cleaned so it never contains the API key, request headers or response details.
- Short-lived errors (HTTP 429, 500, 502, 503, 504) are retried by the Gemini SDK, at most **3 attempts** in total with short waits. Permanent errors such as 400, 403 and 404 are not retried.
- Ctrl+C exits cleanly without a traceback. If pressed while waiting for Gemini, it is logged as `ai_error` (cancelled by staff), never `sent`.

Log statuses in `status_log.json`: `sent`, `rejected`, `escalation_not_approved`, `invalid_ai_output`, `ai_error`.

## Technology stack

- Python 3 (developed on Python 3.13.13)
- Google Gemini API via the `google-genai` package (free key from Google AI Studio)
- `pydantic` for validating the AI's JSON output
- `python-dotenv` for loading settings from `.env`
- `pytest` for automated tests (Gemini is mocked, so no API key is needed)

Dependencies in `requirements.txt` are unpinned.

## Project structure

```text
rahn-assessment/
├── main.py                    # Entry point
├── requirements.txt           # Python dependencies
├── pytest.ini                 # Lets pytest find the fitdesk package
├── .env.example               # Template for settings; never put a real key here
├── .gitignore                 # Keeps .env, virtual environments and status_log.json out of Git
├── data/
│   └── fitdesk_data.json      # Approved packages/prices and Saturday availability (the only source of facts)
├── fitdesk/                   # Application package
│   ├── cli.py                 # Command-line flow: enquiry -> AI -> draft -> approval -> log
│   ├── gemini_client.py       # Gemini API wrapper (the only module meant to use the network)
│   ├── models.py              # Pydantic models for the AI output and the log record
│   ├── knowledge_base.py      # Loads and queries the data file
│   ├── response_builder.py    # Builds the draft reply or the escalation phrase
│   ├── approval.py            # "Send? (y/n)" approval step
│   └── audit_log.py           # Writes outcomes to status_log.json
├── tests/                     # pytest tests (Gemini mocked, network blocked)
└── docs/
    ├── SRS.md                 # Requirements, acceptance criteria, assumptions
    ├── REGRESSION_TESTS.md    # Regression tests with actual results
    └── RAPLH_LOG.md           # Record of AI-assisted work iterations
```

## Prerequisites

- Windows with PowerShell
- Python 3 installed and available as `python` (check with `python --version`)
- Git
- A free Gemini API key from [Google AI Studio](https://aistudio.google.com/) (needed to run the assistant, not to run the tests)

## Setup (Windows PowerShell)

1. **Clone the repository**

   ```powershell
   git clone https://github.com/nyamfusima/rahn-assessment-sima-nyamfu.git
   cd rahn-assessment-sima-nyamfu
   ```

2. **Create and activate a virtual environment**

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

   If PowerShell blocks the activation script, run this once for the current window and activate again:

   ```powershell
   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
   ```

3. **Install dependencies**

   ```powershell
   pip install -r requirements.txt
   ```

4. **Configure the Gemini API key**

   Copy the template to a real `.env` file:

   ```powershell
   Copy-Item .env.example .env
   ```

   Open `.env` and replace the placeholder values:

   ```text
   GEMINI_API_KEY=<your key from Google AI Studio>
   GEMINI_MODEL=<a Gemini model name available to your key>
   ```

   Optional: `GEMINI_TIMEOUT_SECONDS=30` (default 30). This is the limit for **each** attempt. With up to 3 attempts, one enquiry can wait up to about 100 seconds before the call is treated as failed and nothing is sent.

   - `.env.example` is only a **template**. It must **never** contain a real key, because it is committed to Git.
   - `.env` holds your real key. It is listed in `.gitignore` and must never be committed or shared.

## Run

With the virtual environment active, either type the message when asked:

```powershell
python main.py
```

or pass it in quotes:

```powershell
python main.py "How much is the 12-session pack and do you have Saturday slots?"
```

The program handles one enquiry per run:

1. It shows the draft reply.
2. It asks `Send? (y/n)`.
3. It appends the outcome to `status_log.json` in the project folder. This file is git-ignored and stays on your computer.

Example of a draft for the message above (taken from a test run with Gemini mocked):

```text
Draft reply:
  The 12 sessions package costs R1,680. Saturday slots available: 09:00, 11:00; full: 10:00.
Send? (y/n)
```

Exit codes:

- `0`: an enquiry was processed. This includes when staff answered `n`.
- `1`: the AI failed, timed out or returned invalid output. Nothing was sent, and the failure was logged.
- `2`: a setup problem, such as a missing key or model, an unreadable data file, a corrupt log or an empty message.
- `130`: cancelled with Ctrl+C. Nothing was sent.

## Test

```powershell
python -m pytest
```

Checked on Python 3.13.13 with `google-genai` 3.6.1: **67 passed**. The tests need no API key and make no network calls. A fixture unsets the Gemini settings and blocks sockets, and Gemini is replaced by a fake. The retry tests use the real Gemini SDK against a fake HTTP server. Test descriptions and results are in `docs/REGRESSION_TESTS.md`.

## AI use

- **Claude Code** (Anthropic's AI coding tool) was used to help with:
  - the project scaffolding (folder structure, placeholder files, `.gitignore`, `.env.example`)
  - drafting `docs/SRS.md` and filling `data/fitdesk_data.json`
  - drafting this README
  - checking the brief and Playbook requirements
  - implementing the Phase 3 code in `fitdesk/` and `main.py`, writing the pytest tests, and filling `docs/REGRESSION_TESTS.md` with the actual results
  - investigating the live Gemini `ServerError` (HTTP 503/504) and implementing the fix: a clear, safe error message, bounded retries and clean Ctrl+C handling (Iteration 4)
  - drafting the `docs/RAPLH_LOG.md` entries and the two reflection answers at the end of that log
- **ChatGPT** (OpenAI) was used for: understanding the requirements in the brief, and writing the prompts I gave to Claude Code.
- Each step was reviewed by me before it was accepted. Iterations are recorded in `docs/RAPLH_LOG.md`.
- **Claude model:** Claude Opus, used in Claude Code for planning, architecture and implementation, and on claude.ai for a final check of the submission against the brief.
- The Working style answers below are written by me, without AI.

## What doesn't work yet

- **Live use is proven on one model only.** With `GEMINI_MODEL=gemini-3.5-flash-lite`, a live run on 2026-11-20 showed that Gemini's structured output passes the Pydantic model. The draft was built from the data file only, and the `y` approval recorded `sent`. Other models have not been proven:
  - **`gemini-3.8-flash`** returned only **503 UNAVAILABLE** ("high demand") or **504 DEADLINE_EXCEEDED** that day. The app handled this correctly: it showed the HTTP status, retried at most 3 times and logged `ai_error`, with nothing sent. A successful response from that model has not been seen.
- **The default 30 s timeout can be too short under load.** The timeout applies to each attempt and is also sent to Google as the server deadline, so a busy model can hit it and return 504. **Recommended: `GEMINI_TIMEOUT_SECONDS=90`**, which is what the successful live run used. The code default is still 30 s.
- **Ctrl+C during a live call** is covered by automated tests only. It has not been tried by hand during a real request.
- **`GEMINI_MODEL` has no default.** You must set a model name that your key can use. `gemini-3.5-flash-lite` is the one proven live.
- **Classification quality depends on Gemini.** If Gemini labels a question wrongly, the draft can still only contain facts from the data file. But it may then answer a different question from the one asked, or escalate when it did not need to. Staff approval is the safeguard.
- **Times like "9am" are escalated.** The time matcher accepts `09:00`, `9:00`, `0900` and `9h00`, but not am/pm forms. Gemini is told to return 24-hour times, and anything else escalates (safe, but not ideal).
- **Dependencies are unpinned** in `requirements.txt`. Tested versions: `google-genai` 3.6.1, `pydantic` 2.14.4, `python-dotenv` 1.2.4, `pytest` 9.2.0.
- **Design limits by intent:**
  - one enquiry per run;
  - drafts cannot be edited by staff;
  - "sent" is a log status only;
  - the data file has Saturday times without dates (see the assumptions in `docs/SRS.md`).

## Working style

### 1. It is 22:00, and you have been stuck on the same error for three hours. What do you do next, step by step?

The first step is to stop editing and read the actual error, because three hours of the same failure means I am guessing. I go back to the last known working state and reproduce it once, deliberately. Then I read the full message and the logs rather than the summary. Next I test one variable at a time: settings, timeout, credentials, network. That is how I found my Gemini calls were failing, and the 429 that showed my free tier quota was exhausted on an old account. A new key, gemini-3.5-flash-lite instead of gemini-3.8-flash, and a timeout of 90 seconds fixed it. I also write down what I have tried, so the morning is not a restart. Past midnight, I stop.


### 2. It is Wednesday. Your teammate has not replied to messages since Monday, and you present together on Friday. What do you do?

I chase once, with a deadline attached. I message them on Wednesday morning saying I need their part by Thursday noon to assemble Friday, and I offer to take whichever piece they are least likely to reach. Meanwhile I assume nothing arrives and build around my own sections, leaving clear gaps for theirs. If Thursday noon passes, I tell the mentor a section may be missing, before Friday rather than during it. On the day I present my part properly and cover what I can of theirs without pretending it is finished. What I avoid is sitting quietly until Thursday night and then panicking. Silence is usually workload or something personal, not disinterest, so I stay light about it.


### 3. Your mentor tells you that the approach you have spent two days on is wrong. How do you react, and what do you do next?

My first reaction is to ask what specifically is wrong, because "wrong" covers a lot and only part of it is usually true. If the mentor can point at a concrete flaw, I accept it quickly and change that part. That happened with the Gemini model. The calls kept failing, the model choice looked like the problem, and the obvious move was to abandon it. Instead I checked, and the real fault was an exhausted quota on my account and a timeout that was too short. The fix was configuration, not a rebuild. Two days of work stays if the diagnosis is right. What I try not to do is defend the work out of sunk cost.


### 4. From January to March 2027, you must attend sessions every Monday, Wednesday and Friday. What in your life could get in the way, and what is your plan for each thing?

Remote makes power and internet the two real risks, so both get a plan. Load shedding first: I check the schedule weekly, keep a charged laptop and a power bank, and know which nearby places have power and wifi so a session is never simply lost. Second, internet failure: a phone hotspot as backup, a data bundle I do not burn through, and a voice only fallback if video will not hold. Third, a daytime commitment at home, since Monday, Wednesday and Friday do not come free by default. I block those slots now and tell the people I live with that they are fixed. If a session is lost anyway, I ask for the notes and catch up before the next one.

