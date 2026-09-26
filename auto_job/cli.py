from __future__ import annotations
import argparse, json, os, subprocess, sys
from pathlib import Path
import yaml
from .answers import answer_question
from .eligibility import evaluate_eligibility
from .matching import technical_fit
from .pdf_verify import verify_pdf
from .profile import ROOT, load_profile, assert_no_unconfirmed_ms
from .scout import latest_report, run_scout
from .evaluator import evaluate_pending

def _scan(args):
    root = ROOT; upstream = root / 'third_party' / 'career-ops'
    if not (upstream / 'scan.mjs').exists():
        print('Career-Ops submodule is unavailable; run git submodule update --init', file=sys.stderr); return 2
    env = os.environ.copy(); env['CAREER_OPS_ROOT'] = str(root); env['CAREER_OPS_PORTALS'] = str(root / 'config' / 'portals.yml')
    node = os.environ.get('AUTO_JOB_NODE') or 'node'
    if node != 'node' and not Path(node).exists(): node = 'node'
    cmd = [node, str(upstream / 'scan.mjs'), '--json']
    if args.dry_run: cmd.append('--dry-run')
    if args.since is not None: cmd += ['--since', str(args.since)]
    p = subprocess.run(cmd, cwd=upstream, env=env, text=True, capture_output=True)
    print(p.stdout, end=''); print(p.stderr, file=sys.stderr, end=''); return p.returncode

def _status(_):
    print(f"Jobs on disk: {len(list((ROOT / 'jobs').glob('*/metadata.yml')))}")
    print(f"Tracker: {ROOT / 'data' / 'applications.md'}")
    return 0

def _evaluate(args):
    jd = Path(args.jd).read_text(encoding='utf-8') if args.jd else args.text
    print(json.dumps({'eligibility': evaluate_eligibility(jd, load_profile()).to_dict(), 'fit': technical_fit(args.title, jd)}, indent=2)); return 0

def _prepare(args):
    job_dir = ROOT / 'jobs' / args.job_id
    if not job_dir.exists(): print(f'Unknown job id: {args.job_id}', file=sys.stderr); return 2
    profile = load_profile(); jd = (job_dir / 'job.md').read_text(encoding='utf-8')
    for artifact in job_dir.glob('*'):
        if artifact.suffix.lower() in {'.md', '.tex', '.txt'}:
            assert_no_unconfirmed_ms(artifact.read_text(encoding='utf-8'), profile)
    e = evaluate_eligibility(jd, profile)
    if e.overall == 'FAIL': print('Preparation blocked by eligibility FAIL; review the saved evaluation first.', file=sys.stderr); return 3
    (job_dir / 'evaluation.md').write_text('# Eligibility\n\n```yaml\n' + yaml.safe_dump(e.to_dict(), sort_keys=False) + '```\n', encoding='utf-8')
    print('Read prompts/prepare.md, map JD requirements to verified evidence, draft, then run prompts/reviewer.md.'); return 0

def _verify(args):
    r = verify_pdf(Path(args.pdf), args.term); print(json.dumps({k:v for k,v in r.items() if k != 'text'}, indent=2)); return 0 if r['ats_text_extraction'] == 'PASS' else 1

def _answer(args): print(json.dumps(answer_question(args.question, load_profile()), indent=2)); return 0

def _validate(args):
    profile = load_profile()
    assert_no_unconfirmed_ms(Path(args.file).read_text(encoding='utf-8'), profile)
    print('PASS: profile and artifact satisfy the graduate-school claim guard.'); return 0

def _scout_run(args):
    result = run_scout(dry_run=args.dry_run, since=args.since, report=not args.no_report)
    print(json.dumps({"status": result.status, "returncode": result.returncode, "scanned": result.scanned,
                      "added": result.added, "evaluated": result.evaluated, "report": str(result.report_path) if result.report_path else None,
                      "errors": result.errors or []}, indent=2))
    return 0 if result.status == "success" else 2

def _scout_last(_):
    path = latest_report()
    if not path:
        print("No daily scout report has been generated.")
        return 1
    print(path.read_text(encoding="utf-8"), end="")
    return 0

def _evaluator_run(args):
    result = evaluate_pending(dry_run=args.dry_run, job_id=args.job_id)
    print(json.dumps(result, indent=2))
    return 0

def _orchestration_status(_):
    cfg = ROOT / "config" / "paperclip.yml"
    config = yaml.safe_load(cfg.read_text(encoding="utf-8")) if cfg.exists() else {}
    paperclip = config.get("paperclip", {}) if isinstance(config, dict) else {}
    auth = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / "auth.json"
    print(json.dumps({"enabled": bool(paperclip.get("enabled", False)), "config": str(cfg),
                      "paperclip_url": os.environ.get("PAPERCLIP_API_URL", "http://localhost:3100"),
                      "codex_cli": bool(__import__('shutil').which("codex")),
                      "codex_auth_file_present": auth.is_file() and auth.stat().st_size > 0,
                      "latest_report": str(latest_report()) if latest_report() else None,
                      "project": paperclip.get("project", {}), "scout": paperclip.get("scout", {}),
                      "evaluator": paperclip.get("evaluator", {})}, indent=2))
    return 0

def _paperclip_open(_):
    url = os.environ.get("PAPERCLIP_API_URL", "http://localhost:3100")
    try:
        subprocess.Popen(["open", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"Opened {url}")
    except FileNotFoundError:
        print(url)
    return 0

def main(argv=None):
    p=argparse.ArgumentParser(prog='auto-job'); sub=p.add_subparsers(dest='command', required=True)
    s=sub.add_parser('scan'); s.add_argument('--dry-run', action='store_true'); s.add_argument('--since', type=int); s.set_defaults(func=_scan)
    s=sub.add_parser('status'); s.set_defaults(func=_status)
    s=sub.add_parser('evaluate'); s.add_argument('--jd'); s.add_argument('--text', default=''); s.add_argument('--title', default=''); s.set_defaults(func=_evaluate)
    s=sub.add_parser('prepare'); s.add_argument('job_id'); s.set_defaults(func=_prepare)
    s=sub.add_parser('verify'); s.add_argument('pdf'); s.add_argument('--term', action='append', default=[]); s.set_defaults(func=_verify)
    s=sub.add_parser('answer'); s.add_argument('question'); s.set_defaults(func=_answer)
    s=sub.add_parser('validate'); s.add_argument('file'); s.set_defaults(func=_validate)
    s=sub.add_parser('scout'); scout_sub=s.add_subparsers(dest='scout_command', required=True)
    s=scout_sub.add_parser('run'); s.add_argument('--dry-run', action='store_true'); s.add_argument('--since', type=int); s.add_argument('--no-report', action='store_true'); s.set_defaults(func=_scout_run)
    s=scout_sub.add_parser('last'); s.set_defaults(func=_scout_last)
    s=sub.add_parser('evaluator'); ev_sub=s.add_subparsers(dest='evaluator_command', required=True)
    s=ev_sub.add_parser('run'); s.add_argument('--dry-run', action='store_true'); s.add_argument('--job-id'); s.set_defaults(func=_evaluator_run)
    s=sub.add_parser('orchestration'); orch_sub=s.add_subparsers(dest='orchestration_command', required=True)
    s=orch_sub.add_parser('status'); s.set_defaults(func=_orchestration_status)
    s=sub.add_parser('paperclip'); pc_sub=s.add_subparsers(dest='paperclip_command', required=True)
    s=pc_sub.add_parser('open'); s.set_defaults(func=_paperclip_open)
    parsed = p.parse_args(argv)
    return parsed.func(parsed)

if __name__ == '__main__': raise SystemExit(main())
