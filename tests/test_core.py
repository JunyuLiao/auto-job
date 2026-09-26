from pathlib import Path
import pytest
from auto_job.answers import answer_question
from auto_job.eligibility import evaluate_eligibility
from auto_job.matching import technical_fit
from auto_job.profile import load_profile, assert_no_unconfirmed_ms
from auto_job.scout import deduplicate_postings
from auto_job.evaluator import _priority
import auto_job.scout as scout

PROFILE = load_profile()

def test_no_sponsorship_passes():
    e = evaluate_eligibility('Must be authorized to work in the United States. No sponsorship.', PROFILE)
    assert e.overall == 'PASS'

def test_citizens_only_fails():
    e = evaluate_eligibility('U.S. citizens only.', PROFILE)
    assert e.work_authorization == 'FAIL'
    assert e.overall == 'FAIL'

def test_explicit_2027_2028_range_fails_without_ms():
    e = evaluate_eligibility('Expected graduation December 2027 through June 2028.', PROFILE)
    assert e.graduation_window == 'FAIL'
    assert e.overall == 'FAIL'

def test_return_to_school_is_soft_note():
    e = evaluate_eligibility('Must return to school for at least one semester after internship.', PROFILE)
    assert e.return_to_school == 'SOFT_NOTE'
    assert e.overall != 'FAIL'

def test_current_enrollment_uses_real_undergraduate_status():
    e = evaluate_eligibility('Currently pursuing a bachelor degree.', PROFILE)
    assert e.enrollment == 'PASS'

def test_ms_claim_is_blocked():
    with pytest.raises(ValueError):
        assert_no_unconfirmed_ms('Incoming M.S. in Computer Science', PROFILE)

def test_generic_title_content_is_high_fit():
    fit = technical_fit('Software Engineer Intern', 'CUDA, Triton, LLM inference, GPU kernel optimization')
    assert fit['level'] == 'very_high'
    assert fit['score'] >= 36

def test_unknown_cuda_years_requires_manual_review():
    result = answer_question('How many years of production CUDA experience do you have?', PROFILE)
    assert result['level'] == 'manual-review'
    assert result['answer'] is None

def test_scout_deduplicates_without_rewriting_canonical_state():
    fresh, seen = deduplicate_postings([
        {"id": "a", "url": "https://example/a"},
        {"id": "a", "url": "https://example/a-duplicate"},
        {"url": "https://example/b"},
    ], {"a"})
    assert [row.get("url") for row in fresh] == ["https://example/b"]
    assert seen == {"a", "https://example/b"}

def test_evaluator_priority_uses_canonical_eligibility_and_fit_levels():
    assert _priority("FAIL", "very_high") == "C"
    assert _priority("PASS", "very_high") == "A"
    assert _priority("PASS", "medium") == "B"
    assert _priority("UNCERTAIN", "low") == "C"

def test_scout_report_distinguishes_infrastructure_failure(tmp_path, monkeypatch):
    class Completed:
        returncode = 2
        stdout = '{"version":"careerops.scan.receipt@1","scanned":3,"added":0,"errors":[{"company":"Example","error":"timeout"}]}\n'
        stderr = ''
    monkeypatch.setattr(scout.subprocess, "run", lambda *a, **k: Completed())
    report = tmp_path / "2026-09-27.md"
    monkeypatch.setattr(scout, "_report_path", lambda day=None: report)
    result = scout.run_scout(report=True, day="2026-09-27")
    assert result.status == "failed"
    text = report.read_text()
    assert "Search infrastructure failure" in text
    assert "timeout" in text

def test_scout_report_distinguishes_completed_no_match(tmp_path, monkeypatch):
    class Completed:
        returncode = 0
        stdout = '{"version":"careerops.scan.receipt@1","scanned":4,"added":0,"errors":[]}\n'
        stderr = ''
    monkeypatch.setattr(scout.subprocess, "run", lambda *a, **k: Completed())
    report = tmp_path / "2026-09-27.md"
    monkeypatch.setattr(scout, "_report_path", lambda day=None: report)
    result = scout.run_scout(report=True, day="2026-09-27")
    assert result.status == "success"
    assert "No new matches" in report.read_text()
