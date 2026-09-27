"""Evidence-bound application bundles and deterministic ATS form read-back."""
from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from .private import ensure_private_home, private_home
from .profile import load_profile, verified_facts
from .answers import answer_question


def _digest(value: Any) -> str:
    data = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(data).hexdigest()


def create_bundle(root: Path, job_id: str, resume: Path | None = None, questions: list[str] | None = None) -> dict[str, Any]:
    job = root / "jobs" / job_id
    if not (job / "job.md").exists():
        raise FileNotFoundError(f"unknown job: {job_id}")
    home = ensure_private_home(root)
    profile = load_profile(root)
    facts = verified_facts(profile)
    if not facts and not profile.get("candidate"):
        raise ValueError("no verified candidate facts are available")
    answers = []
    for question in questions or []:
        record = answer_question(question, profile)
        if record.get("answer") is None:
            raise ValueError(f"manual-review required for question: {question}")
        answers.append({"question": question, **record, "source": "verified profile",
                        "scope": job_id, "verified_at": datetime.now(timezone.utc).isoformat()})
    resume = resume or (root / "CV.pdf")
    if not resume.exists():
        raise FileNotFoundError("resume is required to build an application bundle")
    stored_resume = home / "documents" / "generated" / job_id / resume.name
    stored_resume.parent.mkdir(parents=True, exist_ok=True)
    if resume.resolve() != stored_resume.resolve(): shutil.copy2(resume, stored_resume)
    artifact = {"path": str(stored_resume), "sha256": hashlib.sha256(stored_resume.read_bytes()).hexdigest()}
    if answers:
        answer_log = home / "answers" / "verified.jsonl"
        with answer_log.open("a", encoding="utf-8") as stream:
            for record in answers: stream.write(json.dumps(record, sort_keys=True) + "\n")
        try: answer_log.chmod(0o600)
        except OSError: pass
    bundle = {
        "schema": "auto-job.application-bundle.v1", "job_id": job_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "job": {"path": str(job / "job.md"), "sha256": hashlib.sha256((job / "job.md").read_bytes()).hexdigest()},
        "verified_facts": facts, "candidate": profile.get("candidate", {}),
        "education": profile.get("education", {}), "answers": answers, "artifacts": [artifact],
    }
    bundle["facts_hash"] = _digest(facts)
    bundle["bundle_hash"] = _digest(bundle)
    out = home / "applications" / job_id / "bundle.json"
    out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(bundle, indent=2) + "\n", encoding="utf-8")
    try: out.chmod(0o600); stored_resume.chmod(0o600)
    except OSError: pass
    return {"path": str(out), "bundle_hash": bundle["bundle_hash"], "job_id": job_id}


def fill_and_review(root: Path, bundle_path: Path, form_path: Path) -> dict[str, Any]:
    bundle = json.loads(bundle_path.read_text(encoding="utf-8")); form = json.loads(form_path.read_text(encoding="utf-8"))
    values = {a["question"]: a.get("answer") for a in bundle.get("answers", [])}
    facts = bundle.get("verified_facts", {})
    candidate = bundle.get("candidate", {}) if isinstance(bundle.get("candidate"), dict) else {}
    flat = {"candidate": candidate, **candidate}
    if isinstance(facts, dict): flat.update(facts)
    flat["education"] = bundle.get("education", {})
    def lookup(key: str):
        value: Any = flat
        for part in key.split("."):
            if not isinstance(value, dict) or part not in value: return None
            value = value[part]
        return value
    filled, errors = [], []
    for field in form.get("fields", []):
        key, label = str(field.get("key", "")), str(field.get("label", ""))
        # The form description may report an observed DOM value, but can never
        # introduce a candidate value. Expected values come only from the bundle.
        value = lookup(key)
        if value is None:
            value = next((v for q, v in values.items() if q.lower() == label.lower()), None)
        if value is None:
            errors.append({"key": key, "reason": "no verified answer"}); continue
        if field.get("options") and value not in field["options"]:
            errors.append({"key": key, "reason": "value is not an exact option"}); continue
        read_back = field.get("dom_value", value)
        if read_back != value:
            errors.append({"key": key, "reason": "DOM read-back mismatch", "expected": value, "read_back": read_back}); continue
        filled.append({"key": key, "value": value, "read_back": read_back, "validated": True})
    review = {"schema": "auto-job.review.v1", "job_id": bundle.get("job_id"), "bundle_hash": bundle.get("bundle_hash"), "status": "REVIEW_READY" if not errors else "MANUAL_REVIEW", "fields": filled, "errors": errors}
    review["review_hash"] = _digest(review)
    out = private_home(root) / "applications" / str(bundle.get("job_id")) / "review.json"
    out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(review, indent=2) + "\n", encoding="utf-8")
    try: out.chmod(0o600)
    except OSError: pass
    return {"path": str(out), "status": review["status"], "review_hash": review["review_hash"], "errors": errors}
