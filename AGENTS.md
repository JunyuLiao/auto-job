# auto-job instructions for Codex

You are operating an internship-search workspace. Use English output unless the user requests another language. Never call an LLM API for semantic work: reason interactively in Codex or use `codex exec` when explicitly useful. Deterministic scripts live in `auto_job/` and `bin/`.

## Operating rules

- Discovery is delegated to `third_party/career-ops`; set `CAREER_OPS_ROOT` to this repository and do not modify upstream files for personal data.
- Run eligibility separately from technical fit. Preserve exact JD wording for uncertain gates.
- Treat local `config/profile.local.yml` and `profile/evidence.yml` as verified sources. Distinguish verified fact, inferred skill, preference, and generated wording.
- Never invent a metric, technology, title, publication, ownership claim, enrollment status, or answer.
- Any unconfirmed graduate-school plan is not a verified fact and cannot be used to pass a graduation or enrollment test.
- Unknown application questions are `manual-review`; never randomize or silently guess. Never auto-submit LinkedIn.
- Paperclip is optional orchestration only. Keep canonical job/profile/eligibility state in auto-job and Career-Ops; use `./bin/auto-job scout run` and `./bin/auto-job evaluator run` for agent work.
- For Priority A use `prompts/prepare.md` and `prompts/reviewer.md`; reviewer criticism precedes revision.
- After any PDF generation, run `./bin/auto-job verify` and check actual extracted text, reading order, contacts, garbled characters, and supported JD terms.
- Before presenting any generated resume or application artifact, run `./bin/auto-job validate <file>`; this blocks unconfirmed graduate-school wording.

## User phrases

- “scan for new jobs”: run a Career-Ops scan, then deterministic eligibility/fit triage and a concise report.
- “triage today’s jobs”: inspect new postings, classify eligibility, score technical signals, and surface deadlines.
- “prepare application for job <id>”: follow the evidence map, draft, independent review, revision, PDF verification, and answer preparation workflow.
- “review application for job <id>”: critique unsupported claims, missing supported terms, ATS text, and education consistency.
- “show my pipeline”: inspect Career-Ops tracker and summarize statuses/outcomes without changing them.
