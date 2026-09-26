from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Any


PASS, SOFT_NOTE, UNCERTAIN, FAIL = "PASS", "SOFT_NOTE", "UNCERTAIN", "FAIL"


@dataclass
class Eligibility:
    overall: str
    work_authorization: str
    degree: str
    graduation_window: str
    enrollment: str
    return_to_school: str
    internship_dates: str = UNCERTAIN
    notes: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["notes"] = d["notes"] or []
        return d


def _explicit_graduation_range(text: str) -> tuple[int, int] | None:
    t = text.lower()
    # Explicit year range is the hard check. Months/terms are retained in notes.
    years = [int(y) for y in re.findall(r"\b20\d{2}\b", t)]
    if len(years) >= 2 and re.search(r"graduat|degree|class of|expected", t):
        return min(years), max(years)
    return None


def evaluate_eligibility(jd: str, profile: dict[str, Any]) -> Eligibility:
    t = jd.lower()
    notes: list[str] = []
    authorization = str(profile.get("candidate", {}).get("work_authorization", "")).lower()
    if re.search(r"u\.s\. citizens? only|us citizens? only|must be a citizen", t) and "citizen" not in authorization:
        work = FAIL
        notes.append("Posting appears to require U.S. citizenship; the local profile does not verify citizenship.")
    elif re.search(r"no sponsorship|will not sponsor|unable to sponsor|must .*authorized|authorized to work in the united states", t):
        work = PASS
    else:
        work = PASS if "authorized to work in the united states" in t else UNCERTAIN

    rng = _explicit_graduation_range(jd)
    if rng:
        # Current verified bachelor's graduation is May 2027. A future, unconfirmed
        # M.S. cannot satisfy a hard date range.
        # The verified date is May 2027. A range beginning after May 2027 does
        # not include it even when the year itself is 2027.
        starts_after_verified = rng[0] > 2027 or (rng[0] == 2027 and bool(re.search(r"december|dec\.?", t)))
        grad = PASS if rng[0] <= 2027 <= rng[1] and not starts_after_verified else FAIL
        if grad == FAIL:
            notes.append(f"Explicit graduation years {rng[0]}-{rng[1]} do not include verified May 2027 graduation.")
    else:
        grad = UNCERTAIN

    if re.search(r"return to school|returning to school|academic term remaining|continue studies", t):
        return_school = SOFT_NOTE
        notes.append("Return-to-school language surfaced for human review; it is not an automatic blocker.")
    else:
        return_school = UNCERTAIN

    if re.search(r"currently pursuing|currently enrolled|enrolled in a degree", t):
        enrollment = PASS  # verified undergraduate is current through May 2027
    else:
        enrollment = UNCERTAIN
    degree = PASS if re.search(r"bachelor|master|computer science|student", t) else UNCERTAIN
    # Unknown details remain visible in component fields, but only a hard
    # incompatibility rejects a posting. This keeps discovery broad.
    overall = FAIL if FAIL in (work, grad) else PASS
    return Eligibility(overall, work, degree, grad, enrollment, return_school, UNCERTAIN, notes)
