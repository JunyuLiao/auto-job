from __future__ import annotations

from pathlib import Path
from typing import Any
import yaml


ROOT = Path(__file__).resolve().parents[1]


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_profile(root: Path = ROOT) -> dict[str, Any]:
    local = root / "config" / "profile.local.yml"
    return load_yaml(local if local.exists() else root / "config" / "profile.yml")


def ms_plan_confirmed(profile: dict[str, Any]) -> bool:
    plan = profile.get("education", {}).get("ms_plan", {})
    return bool(plan.get("admission_confirmed") and plan.get("enrollment_confirmed"))


def verified_facts(profile: dict[str, Any]) -> dict[str, Any]:
    """Return the facts that may be used as evidence, never generated wording."""
    return profile.get("verified_facts", {})


def assert_no_unconfirmed_ms(text: str, profile: dict[str, Any]) -> None:
    if ms_plan_confirmed(profile):
        return
    lowered = text.lower()
    forbidden = ("incoming m.s.", "incoming ms", "m.s. in computer science",
                 "ms in computer science")
    if any(term in lowered for term in forbidden):
        raise ValueError("Blocked: the unconfirmed graduate-school plan cannot be used as a verified claim.")
