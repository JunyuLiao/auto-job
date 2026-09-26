# Paperclip orchestration

Paperclip is an optional scheduler and history layer around this repository. The repository and Career-Ops remain the source of truth for profile facts, job records, eligibility, matching, evidence, and application materials. Paperclip stores only the organization, project, agent, routine, run history, and links to reports.

The checked-in topology is:

- Organization: `Personal Career Search`
- Goal: `Find the best Summer 2027 U.S. internship opportunities`
- Project: `Summer 2027 Job Search`
- Agents: `Job Scout` (daily discovery) and `Job Evaluator` (manual deeper review)
- Routine: `Job Scout`, `30 10 * * *` (10:30 AM), local timezone, `coalesce_if_active`, `skip_missed`

Run `./orchestration/paperclip/bootstrap.sh --check` to verify prerequisites. Run `./orchestration/paperclip/bootstrap.sh --onboard` once to initialize a local Paperclip instance, then `./orchestration/paperclip/configure.sh --apply` with a local Paperclip API key. `configure.sh` is idempotent by name and prints its plan without making changes unless `--apply` is provided.

Paperclip’s current local adapter is `codex_local`. It uses the host Codex login through the managed Codex home; no OpenAI API key is needed. The launcher sets `PAPERCLIP_TELEMETRY_DISABLED=1` by default. Remove that export only if anonymous telemetry is intentionally desired.

Start and stop the local server with `./orchestration/paperclip/bootstrap.sh --run` and Ctrl-C. The local process must be running for scheduled routines; missed runs are skipped and are not replayed later.
