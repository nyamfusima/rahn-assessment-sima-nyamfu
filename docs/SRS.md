# SRS: FitDesk Enquiry Assistant

Source tags: **A** = At-Home Technical Assessment (section), **P** = Hermanus AI Agent Playbook (section). Example: A05.4 = Assessment section 05, item 4.

## 1. Business objective
- The studio owner wants a command-line assistant that answers package-price and Saturday-availability enquiries from approved data, so staff spend less time on repetitive replies. (A03; P01)
- Staff stay in control: nothing is recorded as sent without their approval. (A03; P03 Rule 2)

## 2. Stakeholders
- **Studio owner**: owns the price list and availability data; wants accurate, approved replies.
- **Staff member**: runs the tool, reads each draft, answers y or n.
- **Customer**: asks the question; must never receive an invented price or availability claim.
- **RAHN assessors**: review the requirements, code, tests and logs. (A01)

## 3. Scope
- **In scope**: read one typed enquiry; classify it with Gemini into structured JSON; look up facts in the local data file; draft a reply; ask staff for approval; write the outcome to `status_log.json`. (A05)
- **Out of scope**: WhatsApp or any messaging integration, bookings, payments, calendar, client records, weekly check-ins, any UI or web app, and actually delivering a message. (A03; A05; P01)
- In this project "sent" is a status in the log only; nothing is delivered to the customer. (A03: "recording it as sent")

## 4. Functional requirements
- **FR-01**: The system accepts one customer message typed at the command line. (A05.1)
- **FR-02**: The system sends the message to the Gemini API and receives JSON containing at least `intent`, `details` and `requires_human_approval`, validated by a Pydantic model. (A05.2)
- **FR-03**: The system looks up facts only in `data/fitdesk_data.json` (packages and Saturday slots). (A03; A05.3; P03 Rule 1)
- **FR-04**: The draft reply uses only facts from the data file. If an answer is not in the file, the reply says exactly: `I'll check with the owner and come back to you.` The system never guesses. (A05.4; P03 Rule 1)
- **FR-05**: The system prints the draft and asks `Send? (y/n)`. (A05.5; P03 Rule 2)
- **FR-06**: The system records the outcome in `status_log.json`. A "sent" status is recorded only if staff answered y, the AI JSON passed validation, the AI call succeeded, and the reply is not an escalation (or staff approved the escalation message). (A05.6)

## 5. Non-functional requirements
- **NFR-01 Security**: The API key is read from `.env`, which is git-ignored. `.env.example` is committed and no key appears in the repo or the log. (A02.6; P04 guardrails)
- **NFR-02 Reliability**: Invalid JSON, a failed call or a timeout from the AI service is handled without crashing and never produces a "sent" record. (A05.6)
- **NFR-03 Cost and testability**: Only free tools are used (Python, GitHub, free Gemini key). Tests run with the Gemini response mocked, with no API key and no paid calls. (A02.5; A06; P04.2)

## 6. Data inputs and outputs
- **Inputs**: customer message (command line); `data/fitdesk_data.json` (single session R180, 5 sessions R800, 12 sessions R1,680; Saturday 09:00 available, 10:00 full, 11:00 available); staff answer (y/n); `GEMINI_API_KEY` and `GEMINI_MODEL` from `.env`.
- **Outputs**: printed draft reply; `Send? (y/n)` prompt; one record per enquiry in `status_log.json` (message, intent, draft, status, timestamp).

## 7. Approval and failure rules
- **Staff answer n**: status is not "sent". The reason is recorded. (A05.6)
- **Staff answer y**: "sent" is recorded only if no other blocking rule applies. (A05.6)
- **Facts missing**: the draft is the exact escalation phrase. It is recorded as "sent" only if staff approve it with y. (A05.4; A05.6)
- **Invalid or non-matching JSON**: no draft is built from it, nothing is "sent", and the failure is recorded. (A05.6)
- **AI failure or timeout**: no "sent" record; the failure is recorded and the program exits cleanly. (A05.6)
- **Any answer other than y or n**: the prompt repeats; it is never treated as y.

## 8. Acceptance criteria (measurable)
- **AC-01** (FR-03, FR-04): Given a valid mocked AI response for "How much is the 12-session pack?", the draft contains R1,680 and no other price.
- **AC-02** (FR-04): Given an enquiry about a package or slot not in the data file (e.g. a 20-session pack, Saturday 14:00), the draft equals the exact escalation phrase and contains no price or availability claim.
- **AC-03** (FR-02, NFR-02): Given mocked output that is not valid JSON or fails the Pydantic model, the log has no "sent" entry.
- **AC-04** (NFR-02): Given a mocked Gemini exception or timeout, the program does not crash and the log has no "sent" entry.
- **AC-05** (FR-05, FR-06): Given staff answer n, the log has no "sent" entry. Given y on a valid, answerable draft, the log has exactly one "sent" entry.
- **AC-06** (FR-06): Given an escalation draft, "sent" is recorded only after y.
- **AC-07** (NFR-03): All automated tests pass with `GEMINI_API_KEY` unset and no network.
- **AC-08** (NFR-01): `git ls-files` shows `.env.example` and no `.env`; `status_log.json` is git-ignored.

## 9. Ambiguities and assumptions
- **Q1: Partly answerable enquiries.** The 12-session price is in the data but the customer also asks something that is not (e.g. Sunday slots). Should the whole reply be escalated?
  **Assumption**: the draft states the facts found in the data and uses the exact escalation phrase for the rest. It counts as an escalation, so it needs y to be recorded as "sent".
- **Q2: Which Saturday?** The data has times only, with no dates. Is it this week's availability, and who updates it?
  **Assumption**: the file is the current weekly availability, maintained by the owner. Replies state times and status without dates. Questions about other days or dates are escalated.
- **Q3: What does "sent" mean?** The brief says "recording it as sent" but excludes WhatsApp.
  **Assumption**: "sent" is a log status only. Nothing is delivered.
- **Q4: Can staff edit a draft?** The brief gives only a y/n step.
  **Assumption**: no editing. Staff answer y or n.
- **Q5: Log status labels.** The brief names only "sent".
  **Assumption**: other outcomes use labels of my choosing (e.g. `rejected`, `invalid_ai_output`, `ai_error`, `escalation_not_approved`).
