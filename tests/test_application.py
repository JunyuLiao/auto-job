import json
from pathlib import Path

from auto_job.application import create_bundle, fill_and_review


def test_bundle_and_exact_readback(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    (root / "jobs" / "j1").mkdir(parents=True)
    (root / "jobs" / "j1" / "job.md").write_text("Build systems", encoding="utf-8")
    (root / "config").mkdir()
    (root / "config" / "profile.local.yml").write_text(
        "candidate:\n  email: a@example.com\n  full_name: Ada\nverified_facts:\n  - systems\n", encoding="utf-8")
    resume = root / "CV.pdf"; resume.write_bytes(b"resume")
    private = tmp_path / "private"; monkeypatch.setenv("AUTO_JOB_HOME", str(private))
    bundle = create_bundle(root, "j1", resume, ["What is your email?"])
    form = tmp_path / "form.json"
    form.write_text(json.dumps({"fields": [{"key": "candidate.email", "label": "Email"}]}), encoding="utf-8")
    result = fill_and_review(root, Path(bundle["path"]), form)
    assert result["status"] == "REVIEW_READY"
    review = json.loads(Path(result["path"]).read_text())
    assert review["fields"][0]["read_back"] == "a@example.com"


def test_unknown_form_value_stops(tmp_path, monkeypatch):
    root = tmp_path / "repo"; (root / "jobs" / "j1").mkdir(parents=True); (root / "config").mkdir()
    (root / "jobs" / "j1" / "job.md").write_text("x", encoding="utf-8")
    (root / "config" / "profile.local.yml").write_text("candidate: {email: a@example.com}\n", encoding="utf-8")
    resume = root / "CV.pdf"; resume.write_bytes(b"resume")
    monkeypatch.setenv("AUTO_JOB_HOME", str(tmp_path / "private"))
    bundle = create_bundle(root, "j1", resume)
    form = tmp_path / "form.json"; form.write_text(json.dumps({"fields": [{"key": "salary", "label": "Salary"}]}))
    assert fill_and_review(root, Path(bundle["path"]), form)["status"] == "MANUAL_REVIEW"
