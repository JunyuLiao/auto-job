# Architecture

`third_party/career-ops` is a pinned MIT-licensed Git submodule at commit `b0805395cc8d462bc9a6a36c0b2ea8921c522e50`. Its scanners, ATS providers, deduplication, tracker, and JD fetching remain upstream. `CAREER_OPS_ROOT` points those scripts at this workspace's personal data root.

The Python wrapper owns profile normalization, eligibility, technical relevance, answer safety, and PDF text-layer verification. Codex supplies semantic work interactively through `AGENTS.md` and the prompts; no provider API key is required.

Ideas intentionally reimplemented from `ai-job-search` commit `120f476a089358363ceaf2528f52edf2854994bd5`: requirement-to-evidence drafting, independent review, PDF extraction, and ATS checks. Ideas from `Auto_job_applier_linkedIn` commit `e0b2401a7a7b333eab0b518e80be5285c3ee85c5`: structured answer levels and reusable factual answers. No code was vendored and no LinkedIn submission automation is included.

