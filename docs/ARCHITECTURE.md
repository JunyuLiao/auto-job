# Architecture

`third_party/career-ops` is a pinned MIT-licensed Git submodule at commit `b0805395cc8d462bc9a6a36c0b2ea8921c522e50`. Its scanners, ATS providers, deduplication, tracker, and JD fetching remain upstream. `CAREER_OPS_ROOT` points those scripts at this workspace's personal data root.

The scout also reads the configured Summer 2027 community lists through `scripts/community_job_sources.py`. Because Career-Ops confines local parser scripts to its checkout, the wrapper stages a temporary copy for the scan and removes it immediately afterward; the pinned submodule is not modified.

The Python wrapper owns profile normalization, eligibility, technical relevance, answer safety, and PDF text-layer verification. Codex supplies semantic work interactively through `AGENTS.md` and the prompts; no provider API key is required.

## Private application boundary

The Git checkout is the public control plane. `AUTO_JOB_HOME` (by default `~/Library/Application Support/auto-job`) is the private data plane and is rejected when placed inside the worktree. It contains `profile/profile.yml`, verified answer records, source evidence, resumes and generated artifacts, per-job `applications/<job-id>/bundle.json` and `review.json`, browser state, and logs. The `private init` command creates owner-only directories and migrates the existing ignored local profile, evidence file, and master CV.

Bundles are content-addressed attestations over the saved JD, resume, verified facts, and exact answers. The `review` command accepts a small JSON FormIR (`{"fields":[{"key":"candidate.email","label":"Email","options":[],"dom_value":"a@example.com"}]}`), fills only values already in the bundle, rejects unknown or non-exact options, compares the reported DOM value exactly, and records the read-back value and review hash. A `REVIEW_READY` result is a stopping point for human approval; this project does not click Submit.

Ideas intentionally reimplemented from `ai-job-search` commit `120f476a089358363ceaf2528f52edf2854994bd5`: requirement-to-evidence drafting, independent review, PDF extraction, and ATS checks. Ideas from `Auto_job_applier_linkedIn` commit `e0b2401a7a7b333eab0b518e80be5285c3ee85c5`: structured answer levels and reusable factual answers. No code was vendored and no LinkedIn submission automation is included.

The evidence-bound bundle, private-home split, exact read-back, resumable review state, and human approval boundary are adapted from the public [Jobops architecture](https://github.com/yuyao-wang/Jobops). This project keeps its existing Career-Ops discovery layer and implements a smaller local contract instead of importing Jobops code.
