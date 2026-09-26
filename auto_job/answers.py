from __future__ import annotations

import re
from typing import Any
from .profile import ms_plan_confirmed

MANUAL_PATTERNS = (r"how many years.*cuda", r"return to school", r"expected graduation", r"graduate enrollment", r"security clearance", r"salary", r"relocat", r"demographic", r"eeo")
DETERMINISTIC = {"full name", "email", "phone", "linkedin", "github", "work authorization", "sponsorship", "university", "degree", "location"}


def classify_question(question: str) -> str:
    q = question.lower().strip()
    if any(re.search(p, q) for p in MANUAL_PATTERNS):
        return "manual-review"
    if any(k in q for k in DETERMINISTIC):
        return "deterministic"
    return "evidence-constrained"


def answer_question(question: str, profile: dict[str, Any]) -> dict[str, Any]:
    level = classify_question(question)
    if level == "manual-review":
        return {"level": level, "answer": None, "reason": "Truth depends on current or ambiguous facts; do not guess."}
    c = profile.get("candidate", {})
    e = profile.get("education", {})
    if level == "deterministic":
        q = question.lower()
        if "name" in q: value = c.get("full_name")
        elif "email" in q: value = c.get("email")
        elif "phone" in q: value = c.get("phone")
        elif "linkedin" in q: value = c.get("linkedin")
        elif "github" in q: value = c.get("github")
        elif "location" in q: value = c.get("location")
        elif "university" in q: value = e.get("undergraduate", {}).get("institution")
        elif "degree" in q: value = e.get("undergraduate", {}).get("degree")
        elif "sponsorship" in q: value = "No sponsorship required for U.S. employment (U.S. permanent resident)."
        else: value = "Authorized to work in the United States as a permanent resident."
        return {"level": level, "answer": value}
    return {"level": level, "answer": None, "reason": "Codex may draft only from verified_facts and must show evidence before use."}

