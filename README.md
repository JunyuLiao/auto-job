# auto-job

`auto-job` is a Codex-first workspace for finding and preparing applications for Summer 2027 U.S. internships. Career-Ops handles job-source scanning, ATS/company discovery, deduplication, JD fetching, and tracking. The wrapper adds candidate-specific eligibility checks, technical-fit triage, evidence-constrained preparation, reviewer prompts, PDF/ATS verification, and a safe answer bank.

The normal workflow is intentionally human-controlled: discover and triage automatically, prepare materials with verified evidence, then review and submit applications yourself. The optional Paperclip layer schedules discovery and keeps run history; it does not submit applications or send messages.

## Setup

```bash
git submodule update --init --recursive
cd third_party/career-ops && pnpm install --ignore-scripts && cd ../..
python3 -m venv .venv
.venv/bin/pip install -e .
```

If editable installation is unavailable in an offline environment, install the two runtime packages with `.venv/bin/pip install PyYAML pypdf`; the `bin/auto-job` launcher can run directly from the checkout.

Copy the public profile template to the local-only file, then fill in your own facts:

```bash
cp config/profile.yml config/profile.local.yml
```

Edit `config/profile.local.yml`, keep `CV.pdf` and `profile/evidence.local.yml` local, and configure `config/portals.yml` with first-party or ATS boards. The loader prefers `config/profile.local.yml` automatically. Personal career materials are ignored by Git and are not part of the public repository.

## Common use cases

### Find new internship postings

Use a dry run first to confirm sources and settings without writing scan state:

```bash
./bin/auto-job scan --dry-run
```

Run the daily workflow when you want results persisted and summarized:

```bash
./bin/auto-job scout run
./bin/auto-job scout last
```

The scout uses the pinned Career-Ops scanner, keeps canonical job data in this repository, applies the existing eligibility and technical-fit logic to saved jobs, and writes a dated report under `reports/daily/`. A completed scan with no new postings is reported separately from a source or network failure.

### Check whether a role fits

For a quick one-off JD check, pass the title and text directly:

```bash
./bin/auto-job evaluate \
  --title 'ML Systems Intern' \
  --text 'Build CUDA kernels and optimize LLM inference on GPUs.'
```

The output separates eligibility from technical fit. Unknown facts stay visible for human review instead of being guessed.

### Prepare a saved application

After a job has been saved under `jobs/<job-id>/`, prepare it through the evidence-constrained workflow:

```bash
./bin/auto-job prepare <job-id>
```

This checks eligibility, protects the unconfirmed graduate-school information, and points to the preparation and reviewer prompts. It does not submit anything.

### Verify a PDF before sending it

Check extracted text, contacts, reading order, and required terms before sharing a resume:

```bash
./bin/auto-job verify output/resume.pdf --term CUDA --term inference
./bin/auto-job validate output/resume.txt
```

### Run the optional Paperclip schedule

Paperclip is useful when you want discovery to happen automatically while your laptop is running:

```bash
./orchestration/paperclip/bootstrap.sh --check
./orchestration/paperclip/bootstrap.sh --onboard
./orchestration/paperclip/configure.sh
PAPERCLIP_API_KEY=... ./orchestration/paperclip/configure.sh --apply
./orchestration/paperclip/bootstrap.sh --run
```

The configured Job Scout routine runs daily at **10:30 AM in the configured local timezone**. It uses `coalesce_if_active` for overlapping runs and `skip_missed` when the laptop was asleep. The Job Evaluator remains manual:

```bash
./bin/auto-job evaluator run
./bin/auto-job orchestration status
./bin/auto-job paperclip open
```

To change the time, edit `config/paperclip.yml` using standard cron syntax, then rerun `configure.sh --apply`. For example, `30 10 * * *` means 10:30 AM every day. See [docs/PAPERCLIP.md](docs/PAPERCLIP.md) for authentication, pause/resume, failure handling, telemetry, and removal.

## Commands

```bash
./bin/auto-job scan --dry-run
./bin/auto-job scan
./bin/auto-job status
./bin/auto-job evaluate --title 'Software Engineer Intern' --text 'CUDA, Triton, LLM inference, GPU kernel optimization'
./bin/auto-job prepare <job-id>
./bin/auto-job verify output/resume.pdf --term CUDA --term inference
./bin/auto-job answer 'How many years of production CUDA experience do you have?'
./bin/auto-job validate output/resume.txt
./bin/auto-job orchestration status
./bin/auto-job scout run
./bin/auto-job scout last
./bin/auto-job evaluator run
./bin/auto-job paperclip open
```

Inside Codex, use: “scan for new jobs”, “triage today’s jobs”, “prepare application for job `<id>`”, “review application for job `<id>`”, or “show my pipeline”. `AGENTS.md` defines these workflows. Final submission is always manual, including LinkedIn.

## Optional Paperclip orchestration

Paperclip is optional: all direct `scan`, `evaluate`, `prepare`, `verify`, and `answer` commands work without it. See [docs/PAPERCLIP.md](docs/PAPERCLIP.md) for the architecture and operating guide.

## Graduate-school guard

Any unconfirmed graduate-school plan is omitted from generated resumes and cannot be used for eligibility. Set the confirmation fields only after the facts are true and verified; leave expected graduation empty until it is known.

## Attribution

Career-Ops, ai-job-search, and Auto_job_applier_linkedIn are MIT-licensed upstream references. Their repository URLs, commits, and adopted mechanisms are documented in `docs/ARCHITECTURE.md`; no upstream code from the latter two is vendored.
