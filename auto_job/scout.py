from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable

from .profile import ROOT
from .private import private_profile_path


@dataclass
class ScoutResult:
    status: str
    report_path: Path | None
    returncode: int
    scanned: int = 0
    added: int = 0
    errors: list[str] | None = None
    urls: list[str] | None = None
    message: str = ""
    evaluated: int = 0


@contextmanager
def _staged_community_parser(upstream: Path):
    """Make the repo-owned parser visible to Career-Ops for one scan.

    Career-Ops intentionally confines local parser scripts to its own checkout.
    The parent project owns this parser, so stage a temporary copy and restore
    the submodule immediately after the child process exits.
    """
    source = ROOT / "scripts" / "community_job_sources.py"
    target = upstream / "scripts" / "auto_job_community_sources.py"
    if not source.exists():
        raise FileNotFoundError(f"community source parser is missing: {source}")
    target.parent.mkdir(parents=True, exist_ok=True)
    previous = target.read_bytes() if target.exists() else None
    shutil.copyfile(source, target)
    try:
        yield
    finally:
        if previous is None:
            target.unlink(missing_ok=True)
        else:
            target.write_bytes(previous)


def _node() -> str:
    configured = os.environ.get("AUTO_JOB_NODE")
    if configured and Path(configured).exists():
        return configured
    return "node"


def _receipt(stdout: str) -> dict[str, Any] | None:
    for line in reversed(stdout.splitlines()):
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and ("sources" in value or "version" in value):
            return value
    return None


def _errors(receipt: dict[str, Any] | None, stderr: str) -> list[str]:
    found: list[str] = []
    if receipt:
        if isinstance(receipt.get("errors"), list):
            for item in receipt["errors"]:
                if isinstance(item, dict):
                    found.append(f"{item.get('company', 'source')}: {item.get('error', 'source failed')}")
                elif item:
                    found.append(str(item))
        for source in receipt.get("sources", []):
            if isinstance(source, dict) and source.get("status") in {"error", "failed"}:
                label = source.get("portal") or source.get("url") or "source"
                detail = source.get("error") or source.get("message") or "source failed"
                found.append(f"{label}: {detail}")
    if not found:
        lines = [re.sub(r"\s+", " ", line).strip() for line in stderr.splitlines() if line.strip()]
        found.extend(lines[-8:])
    return found[:8]


def _report_path(day: str | None = None) -> Path:
    value = day or date.today().isoformat()
    return ROOT / "reports" / "daily" / f"{value}.md"


def _write_report(path: Path, result: ScoutResult, receipt: dict[str, Any] | None, dry_run: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    errors = result.errors or []
    status = "FAILED" if result.status == "failed" else "SUCCESS"
    lines = [
        f"# Daily Job Scout Report — {path.stem}",
        "",
        f"- Status: **{status}**",
        f"- Mode: {'dry-run' if dry_run else 'live'}",
        f"- Generated: {datetime.now().astimezone().isoformat(timespec='seconds')}",
        f"- Scanner return code: `{result.returncode}`",
        f"- Sources/postings scanned: `{result.scanned}`",
        f"- New postings recorded by Career-Ops: `{result.added}`",
        f"- Saved jobs evaluated by auto-job: `{result.evaluated}`",
        "",
    ]
    if result.status == "failed":
        lines += ["## Search infrastructure failure", "", "The scan did not complete reliably. No conclusion about job availability was drawn.", ""]
        if errors:
            lines += ["Details:", ""] + [f"- {e}" for e in errors] + [""]
    elif result.added == 0:
        lines += ["## No new matches", "", "The scanner completed without recording a new posting in this run.", ""]
    else:
        lines += ["## New posting URLs", ""] + [f"- {url}" for url in (result.urls or [])] + [""]
    lines += ["## Human review boundary", "", "This report is discovery metadata. It never submits applications, changes verified facts, or sends messages.", ""]
    if receipt is not None:
        lines += ["## Scanner receipt", "", "```json", json.dumps(receipt, indent=2, sort_keys=True)[:12000], "```", ""]
    path.write_text("\n".join(lines), encoding="utf-8")


def run_scout(*, dry_run: bool = False, since: int | None = None, report: bool = True, day: str | None = None) -> ScoutResult:
    upstream = ROOT / "third_party" / "career-ops"
    if not (upstream / "scan.mjs").exists():
        result = ScoutResult("failed", None, 2, errors=["Career-Ops submodule is unavailable; run git submodule update --init"], message="missing Career-Ops")
        if report:
            result.report_path = _report_path(day)
            _write_report(result.report_path, result, None, dry_run)
        return result
    env = os.environ.copy()
    env["CAREER_OPS_ROOT"] = str(ROOT)
    env["CAREER_OPS_PORTALS"] = str(ROOT / "config" / "portals.yml")
    if private_profile_path(ROOT).exists():
        env["CAREER_OPS_PROFILE"] = str(private_profile_path(ROOT))
    cmd = [_node(), str(upstream / "scan.mjs"), "--json"]
    if dry_run:
        cmd.append("--dry-run")
    if since is not None:
        cmd += ["--since", str(since)]
    try:
        with _staged_community_parser(upstream):
            completed = subprocess.run(cmd, cwd=upstream, env=env, text=True, capture_output=True)
    except Exception as exc:
        result = ScoutResult("failed", None, 2, errors=[f"scan setup: {exc}"], message="scan setup failed")
        if report:
            result.report_path = _report_path(day)
            _write_report(result.report_path, result, None, dry_run)
        return result
    receipt = _receipt(completed.stdout)
    sources = receipt.get("sources", []) if receipt else []
    scanned = int(receipt.get("scanned", receipt.get("total", 0)) or 0) if receipt else 0
    urls: list[str] = []
    if receipt:
        for key in ("added_urls", "new_urls", "urls"):
            value = receipt.get(key)
            if isinstance(value, list):
                urls = [str(x) for x in value if x]
                if urls:
                    break
    added = int(receipt.get("added", len(urls)) or 0) if receipt else len(urls)
    errors = _errors(receipt, completed.stderr) if completed.returncode else []
    failed = completed.returncode != 0 or (bool(sources) and all(isinstance(s, dict) and s.get("status") in {"error", "failed"} for s in sources))
    result = ScoutResult("failed" if failed else "success", None, completed.returncode, scanned, added, errors, urls)
    if result.status == "success":
        # Keep the eligibility and fit implementation in auto-job. Career-Ops owns
        # source normalization/dedup/persistence; this only triages saved records.
        try:
            from .evaluator import evaluate_pending
            triage = evaluate_pending(dry_run=dry_run)
            result.evaluated = int(triage.get("evaluated", 0))
        except Exception as exc:  # a triage failure is visible without losing scan receipt
            result.errors = [f"auto-job triage: {exc}"]
            result.status = "failed"
            result.returncode = 3
    if report:
        result.report_path = _report_path(day)
        _write_report(result.report_path, result, receipt, dry_run)
    return result


def latest_report() -> Path | None:
    reports = sorted((ROOT / "reports" / "daily").glob("*.md"))
    return reports[-1] if reports else None


def deduplicate_postings(postings: Iterable[dict[str, Any]], seen: set[str]) -> tuple[list[dict[str, Any]], set[str]]:
    """Small deterministic helper used by tests; production dedup remains Career-Ops-owned."""
    fresh: list[dict[str, Any]] = []
    updated = set(seen)
    for posting in postings:
        key = str(posting.get("id") or posting.get("url") or "").strip()
        if not key or key in updated:
            continue
        updated.add(key)
        fresh.append(posting)
    return fresh, updated
