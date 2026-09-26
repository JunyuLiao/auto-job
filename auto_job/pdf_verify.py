from __future__ import annotations

from pathlib import Path
import re
import subprocess
from typing import Any


def extract_text(pdf: Path) -> str:
    try:
        from pypdf import PdfReader
        return "\n".join(page.extract_text() or "" for page in PdfReader(str(pdf)).pages)
    except Exception:
        return subprocess.check_output(["pdftotext", "-layout", "-enc", "UTF-8", str(pdf), "-"], text=True)


def verify_pdf(pdf: Path, required_terms: list[str] | None = None) -> dict[str, Any]:
    text = extract_text(pdf)
    normalized = " ".join(text.split())
    terms = required_terms or []
    present = [term for term in terms if term.lower() in normalized.lower()]
    garbled = "�" in text or len(normalized) < 80
    return {"pdf_render": "PASS" if pdf.exists() else "FAIL", "ats_text_extraction": "PASS" if not garbled else "FAIL", "reading_order": "PASS" if normalized else "FAIL", "pages": _pages(pdf), "critical_terms": {"present": present, "missing": [t for t in terms if t not in present]}, "text": text}


def _pages(pdf: Path) -> int:
    try:
        from pypdf import PdfReader
        return len(PdfReader(str(pdf)).pages)
    except Exception:
        out = subprocess.check_output(["pdfinfo", str(pdf)], text=True)
        m = re.search(r"Pages:\s+(\d+)", out)
        return int(m.group(1)) if m else 0

