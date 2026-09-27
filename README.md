# auto-job

`auto-job` is a Codex-first workspace for finding and preparing applications for Summer 2027 U.S. internships. The pinned Career-Ops submodule owns source scanning, ATS/company discovery, deduplication, job-description fetching, and tracking. This wrapper adds candidate-specific eligibility checks, technical-fit triage, evidence-constrained preparation, PDF/ATS checks, verified answers, and a deterministic application-review boundary.

The application path is:

```text
verified facts → verified answers → immutable bundle → form read-back → REVIEW_READY → human submission
```

Discovery and preparation can be automated. Submission, messaging, and answers that need facts not present in the profile always remain human-controlled. LinkedIn is never submitted automatically.

## Setup

Requirements: Python 3.10+, Node.js, `pnpm`, and a local checkout of the Career-Ops submodule.

```bash
git submodule update --init --recursive
cd third_party/career-ops && pnpm install --ignore-scripts && cd ../..
python3 -m venv .venv
.venv/bin/pip install -e .
```

If editable installation is unavailable offline, install the runtime packages instead:

```bash
.venv/bin/pip install PyYAML pypdf
```

Create the ignored local profile from the public template and fill in only verified facts:

```bash
cp config/profile.yml config/profile.local.yml
```

Keep personal materials in the ignored files `config/profile.local.yml`, `profile/evidence.yml`, and `CV.pdf`. Configure first-party or ATS sources in `config/portals.yml`.

### Private home

Candidate data and application state belong outside the Git worktree. Initialize it once before creating an application bundle:

```bash
./bin/auto-job private init
```

The default is `~/Library/Application Support/auto-job`. Set `AUTO_JOB_HOME` (or the compatibility variable `AUTO_JOB_PRIVATE_HOME`) to choose another directory; it must be outside this repository. The command creates owner-only directories and migrates the local profile, evidence file, and master CV when present. Once an external profile exists, it takes precedence over `config/profile.local.yml`.

The private home contains the profile, verified-answer log, evidence, generated documents, per-job bundles and review records, browser state, and logs. It is never committed.

## Daily job workflow

### 1. Scan sources

Use a dry run to inspect sources without persisting scan state:

```bash
./bin/auto-job scan --dry-run
```

For the normal workflow, run the scout. It invokes Career-Ops, reads the configured first-party/ATS sources plus the live Simplify and SpeedyApply Summer 2027 lists, evaluates saved jobs for eligibility and technical fit, and writes `reports/daily/YYYY-MM-DD.md`:

```bash
./bin/auto-job scout run
./bin/auto-job scout last
```

Useful options are `--since DAYS`, `--dry-run`, and `--no-report`. A successful run with zero new postings is reported as **No new matches**. A scanner or source failure is reported as **Search infrastructure failure** and must not be treated as an empty result.

### 2. Check one role

Pass a saved JD with `--jd`, or provide text directly with `--text`:

```bash
./bin/auto-job evaluate \
  --title 'ML Systems Intern' \
  --text 'Build CUDA kernels and optimize LLM inference on GPUs.'
```

The output keeps eligibility separate from technical fit. Eligibility values are `PASS`, `SOFT_NOTE`, `UNCERTAIN`, or `FAIL`; unknown facts stay visible for review.

### 3. Triage saved jobs

Run the evaluator after a scan, or target one saved job:

```bash
./bin/auto-job evaluator run
./bin/auto-job evaluator run --job-id <job-id>
```

Use `--dry-run` to avoid writing `jobs/*/evaluation.md`. Priority A/B/C is derived from eligibility and technical fit; it does not submit or contact anyone.

### 4. Prepare materials

For a saved job under `jobs/<job-id>/`, run:

```bash
./bin/auto-job prepare <job-id>
```

This writes the deterministic eligibility evaluation and points to [`prompts/prepare.md`](prompts/prepare.md) and [`prompts/reviewer.md`](prompts/reviewer.md). Map every JD requirement to verified evidence, have the reviewer criticize the draft, then revise. Do not add metrics, technologies, titles, publications, ownership claims, or education facts that are not verified.

### 5. Verify a resume or artifact

After generating a PDF, inspect its extracted text, contacts, reading order, garbled characters, and required terms:

```bash
./bin/auto-job verify output/resume.pdf --term CUDA --term inference
./bin/auto-job validate output/resume.txt
```

`verify` returns a non-zero status when text-layer extraction fails. `validate` enforces the graduate-school claim guard. Run both before presenting an artifact.

## Safe application review

The bundle and review commands do not click Submit. They create a private, content-addressed record and stop at `REVIEW_READY` after exact value read-back.

1. Initialize the private home and finish the resume and verified answers.
2. Create a bundle. Repeat `--question` for each deterministic or evidence-backed question; a manual-review question stops the command.

   ```bash
   ./bin/auto-job private init
   ./bin/auto-job bundle <job-id> \
     --resume /path/to/resume.pdf \
     --question 'What is your email?'
   ```

   `--resume` defaults to `CV.pdf` in the worktree. The command prints the private bundle path and hash.

3. Save an exact form snapshot as JSON. `key` is the profile/bundle path, `label` is the visible question, `options` is the exact allowed-option list (or `[]`), and `dom_value` is the value read back from the form:

   ```json
   {
     "fields": [
       {
         "key": "candidate.email",
         "label": "Email",
         "options": [],
         "dom_value": "name@example.com"
       }
     ]
   }
   ```

4. Review the form snapshot against the bundle:

   ```bash
   ./bin/auto-job review \
     "$AUTO_JOB_HOME/applications/<job-id>/bundle.json" \
     form.json
   ```

   The result is saved beside the bundle as `review.json`. `REVIEW_READY` means every field had a verified value and exact read-back. `MANUAL_REVIEW` means a value was missing, not an exact option, or did not match the observed DOM value. Resolve it manually and create a new review; never guess.

## Command reference

```text
scan [--dry-run] [--since DAYS]
status
evaluate (--jd FILE | --text TEXT) [--title TITLE]
prepare JOB_ID
verify PDF [--term TERM]
answer QUESTION
validate FILE
scout run [--dry-run] [--since DAYS] [--no-report]
scout last
evaluator run [--dry-run] [--job-id JOB_ID]
orchestration status
paperclip open
private init
bundle JOB_ID [--resume FILE] [--question QUESTION]
review BUNDLE_JSON FORM_JSON
```

`answer` prints the answer level and a value only when it is available from the verified profile. Questions involving expected graduation, graduate enrollment, return-to-school plans, production CUDA years, clearance, salary, relocation, or demographic data are `manual-review`.

Inside Codex, the supported phrases are “scan for new jobs”, “triage today’s jobs”, “prepare application for job `<id>`”, “review application for job `<id>`”, and “show my pipeline”. [`AGENTS.md`](AGENTS.md) defines those workflows.

## Optional Paperclip scheduling

Paperclip is an optional local scheduler. Direct `scan`, `scout`, `evaluate`, `prepare`, `verify`, and `answer` commands work without it.

```bash
./orchestration/paperclip/bootstrap.sh --check
./orchestration/paperclip/bootstrap.sh --onboard
./orchestration/paperclip/configure.sh
PAPERCLIP_API_KEY=... ./orchestration/paperclip/configure.sh --apply
./orchestration/paperclip/bootstrap.sh --run
```

The default Job Scout routine runs daily at 10:30 in the configured local timezone, coalesces overlapping runs, and skips missed runs while the laptop is asleep. The Job Evaluator remains manual:

```bash
./bin/auto-job evaluator run
./bin/auto-job orchestration status
./bin/auto-job paperclip open
```

Change the schedule in `config/paperclip.yml` using standard cron syntax, then rerun `configure.sh --apply`. See [`docs/PAPERCLIP.md`](docs/PAPERCLIP.md) for authentication, failure handling, telemetry, pause/resume, and removal.

## Guardrails and reference docs

- Eligibility and technical fit are separate checks; see [`docs/ELIGIBILITY.md`](docs/ELIGIBILITY.md).
- An unconfirmed graduate-school plan cannot satisfy an eligibility gate or appear as a verified resume claim.
- Unknown application questions, CAPTCHA, MFA, missing evidence, and ambiguous read-back become `MANUAL_REVIEW`.
- The canonical workflow and private data boundary are described in [`docs/WORKFLOW.md`](docs/WORKFLOW.md) and [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).
- Final submission and outcome tracking are manual.

## Attribution

Career-Ops, ai-job-search, and Auto_job_applier_linkedIn are MIT-licensed upstream references. Repository URLs, commits, and adopted mechanisms are documented in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md); no upstream code from the latter two is vendored.
