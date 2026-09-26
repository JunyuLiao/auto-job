#!/usr/bin/env python3
"""Idempotently materialize config/paperclip.yml in a Paperclip instance."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import urllib.error
import urllib.request
import yaml

ROOT = Path(__file__).resolve().parents[2]


class Api:
    def __init__(self, base: str, key: str):
        self.base = base.rstrip("/")
        self.key = key

    def request(self, method: str, path: str, payload: dict | None = None):
        data = json.dumps(payload).encode() if payload is not None else None
        req = urllib.request.Request(self.base + path, data=data, method=method, headers={
            "Accept": "application/json", "Content-Type": "application/json", "Authorization": f"Bearer {self.key}"
        })
        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                raw = response.read()
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")[:500]
            raise RuntimeError(f"Paperclip API {method} {path} returned HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Paperclip API is unreachable at {self.base}: {exc.reason}") from exc


def first_named(rows, name):
    return next((row for row in rows if isinstance(row, dict) and (row.get("name") == name or row.get("title") == name)), None)


def local_timezone() -> str:
    try:
        resolved = Path("/etc/localtime").resolve()
        marker = "/zoneinfo/"
        text = str(resolved)
        if marker in text:
            return text.split(marker, 1)[1]
    except OSError:
        pass
    return os.environ.get("AUTO_JOB_TIMEZONE", "UTC")


def desired(root: Path) -> dict:
    cfg = yaml.safe_load((root / "config" / "paperclip.yml").read_text(encoding="utf-8"))["paperclip"]
    project = cfg["project"]
    cwd = str(root)
    return {
        "company": {"name": project["organization"], "description": "Personal internship search orchestration."},
        "goal": {"title": project["goal"], "description": "Find and review the strongest Summer 2027 U.S. internship opportunities.", "level": "company", "status": "active"},
        "project": {"name": project["name"], "description": "Canonical auto-job and Career-Ops search workflow.", "status": "planned", "workspace": {"name": "auto-job", "cwd": cwd, "repoRef": "main", "isPrimary": True}},
        "agents": [
            {"name": cfg["scout"]["name"], "role": "scout", "title": "Career job scout", "capabilities": "Discovery, normalization, deduplication, eligibility triage, and reporting", "adapterType": "codex_local", "adapterConfig": {"cwd": cwd, "instructionsFilePath": str(root / "orchestration/paperclip/agents/job-scout.md"), "fastMode": False, "dangerouslyBypassApprovalsAndSandbox": False}},
            {"name": cfg["evaluator"]["name"], "role": "evaluator", "title": "Career job evaluator", "capabilities": "Evidence mapping, fit analysis, strategic prioritization, and review reports", "adapterType": "codex_local", "adapterConfig": {"cwd": cwd, "instructionsFilePath": str(root / "orchestration/paperclip/agents/job-evaluator.md"), "fastMode": False, "dangerouslyBypassApprovalsAndSandbox": False}},
        ],
        "routine": {"title": cfg["scout"]["name"], "description": "Daily discovery through auto-job; no applications or messages.", "priority": "medium", "status": "active", "concurrencyPolicy": cfg["scout"]["concurrency"], "catchUpPolicy": cfg["scout"]["catch_up"], "cronExpression": cfg["scout"]["schedule"], "timezone": cfg["scout"]["timezone"]},
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="write the desired topology to Paperclip")
    parser.add_argument("--dry-run", action="store_true", help="print the desired topology without changing Paperclip")
    args = parser.parse_args(argv)
    plan = desired(ROOT)
    if not args.apply:
        print(json.dumps(plan, indent=2))
        print("Dry run only. Re-run with --apply and PAPERCLIP_API_KEY set to create/update the topology.")
        return 0
    key = os.environ.get("PAPERCLIP_API_KEY")
    if not key:
        print("PAPERCLIP_API_KEY is required for --apply; no credentials were read or printed.")
        return 2
    timezone = plan["routine"]["timezone"]
    if timezone == "local":
        timezone = local_timezone()
        print(f"Using timezone {timezone}; set AUTO_JOB_TIMEZONE to an IANA timezone if needed.")
    api = Api(os.environ.get("PAPERCLIP_API_URL", "http://localhost:3100"), key)
    companies = api.request("GET", "/api/companies")
    company = first_named(companies if isinstance(companies, list) else companies.get("items", []), plan["company"]["name"])
    if not company:
        company = api.request("POST", "/api/companies", plan["company"])
    company_id = company["id"]
    goals = api.request("GET", f"/api/companies/{company_id}/goals")
    goal = first_named(goals if isinstance(goals, list) else goals.get("items", []), plan["goal"]["title"])
    if not goal:
        goal = api.request("POST", f"/api/companies/{company_id}/goals", plan["goal"])
    projects = api.request("GET", f"/api/companies/{company_id}/projects")
    project_payload = dict(plan["project"])
    project_payload["goalIds"] = [goal["id"]]
    project = first_named(projects if isinstance(projects, list) else projects.get("items", []), plan["project"]["name"])
    if not project:
        project = api.request("POST", f"/api/companies/{company_id}/projects", project_payload)
    agents = api.request("GET", f"/api/companies/{company_id}/agents")
    agent_rows = agents if isinstance(agents, list) else agents.get("items", [])
    by_name = {}
    for payload in plan["agents"]:
        agent = first_named(agent_rows, payload["name"])
        if not agent:
            agent = api.request("POST", f"/api/companies/{company_id}/agents", payload)
        by_name[payload["name"]] = agent
    routines = api.request("GET", f"/api/companies/{company_id}/routines")
    routine_rows = routines if isinstance(routines, list) else routines.get("items", [])
    routine = first_named(routine_rows, plan["routine"]["title"])
    routine_payload = {k: v for k, v in plan["routine"].items() if k not in {"cronExpression", "timezone"}}
    routine_payload.update({"assigneeAgentId": by_name[plan["agents"][0]["name"]]["id"], "projectId": project["id"], "goalId": goal["id"]})
    if not routine:
        routine = api.request("POST", f"/api/companies/{company_id}/routines", routine_payload)
        api.request("POST", f"/api/routines/{routine['id']}/triggers", {"kind": "schedule", "cronExpression": plan["routine"]["cronExpression"], "timezone": timezone})
    print(json.dumps({"company_id": company_id, "goal_id": goal["id"], "project_id": project["id"], "agents": {k: v["id"] for k, v in by_name.items()}, "routine_id": routine["id"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
