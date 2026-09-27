#!/usr/bin/env python3
"""Read community-maintained Summer 2027 job lists from GitHub.

The repositories publish their listings as either Markdown tables or an HTML
table in README.md.  This module deliberately emits only the small normalized
shape consumed by Career-Ops' local-parser provider; the live posting remains
the source of truth for the job description and application flow.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from html import unescape
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit
from urllib.request import Request, urlopen


_HREF_RE = re.compile(r"href\s*=\s*['\"]([^'\"]+)['\"]", re.I)
_ROW_RE = re.compile(r"<tr\b[^>]*>(.*?)</tr>", re.I | re.S)
_CELL_RE = re.compile(r"<t[dh]\b[^>]*>(.*?)</t[dh]>", re.I | re.S)
_TAG_RE = re.compile(r"<[^>]+>")


def _text(fragment: str) -> str:
    fragment = re.sub(r"<br\s*/?>", "\n", fragment, flags=re.I)
    value = _TAG_RE.sub(" ", unescape(fragment))
    value = re.sub(r"\s+", " ", value).strip()
    # Community lists use an arrow row to mean "same company as above".
    return value.strip(" |")


def _company(value: str) -> str:
    return re.sub(r"^[^\w]+", "", value, flags=re.UNICODE).strip()


def _hrefs(fragment: str, base_url: str) -> list[str]:
    return [urljoin(base_url, unescape(href).strip()) for href in _HREF_RE.findall(fragment)]


def _canonical_url(value: str) -> str:
    """Drop presentation-only tracking parameters while preserving job IDs."""
    try:
        parts = urlsplit(value)
        path = parts.path
        # Simplify's first link is often an Ashby embedded application form;
        # normalize it to the public posting so Career-Ops can fetch the JD.
        embedded_application = path.rstrip("/").endswith("/application")
        if embedded_application:
            path = path[: -len("/application")]
        query = [(key, item) for key, item in parse_qsl(parts.query, keep_blank_values=True)
                 if not key.lower().startswith("utm_") and key.lower() != "ref"
                 and not (embedded_application and key.lower() == "embed")]
        return urlunsplit((parts.scheme, parts.netloc, path, urlencode(query), parts.fragment))
    except ValueError:
        return value


def _is_posting_url(value: str) -> bool:
    parts = urlsplit(value)
    return parts.scheme in {"http", "https"} and bool(parts.netloc) and "imgur.com" not in parts.netloc.lower()


def _row(company: str, title: str, location: str, links: list[str]) -> dict[str, str] | None:
    company = _company(_text(company))
    title = _text(title)
    location = _text(location)
    posting = next((link for link in links if _is_posting_url(link)), "")
    if not company or not title or not posting:
        return None
    return {
        "company": company,
        "title": title,
        "location": location,
        "url": _canonical_url(posting),
    }


def parse_html_jobs(document: str, source_url: str) -> list[dict[str, str]]:
    """Parse SimplifyJobs' HTML table, including continuation (↳) rows."""
    jobs: list[dict[str, str]] = []
    previous_company = ""
    for raw_row in _ROW_RE.findall(document):
        cells = _CELL_RE.findall(raw_row)
        if len(cells) < 4 or re.search(r"<th\b", raw_row, re.I):
            continue
        company = _company(_text(cells[0]))
        if not company or company == "↳":
            company = previous_company
        if not company:
            continue
        previous_company = company
        links = _hrefs(cells[3], source_url)
        job = _row(company, cells[1], cells[2], links)
        if job:
            jobs.append(job)
    return _dedupe(jobs)


def parse_markdown_jobs(document: str, source_url: str) -> list[dict[str, str]]:
    """Parse the pipe-delimited tables used by the SpeedyApply lists."""
    jobs: list[dict[str, str]] = []
    for line in document.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or "|---" in stripped.replace(" ", ""):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) < 4:
            continue
        # The posting URL is in the Posting column (after optional Salary).
        links = [link for cell in cells[3:] for link in _hrefs(cell, source_url)]
        job = _row(cells[0], cells[1], cells[2], links)
        if job:
            jobs.append(job)
    return _dedupe(jobs)


def _dedupe(jobs: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[str] = set()
    result: list[dict[str, str]] = []
    for job in jobs:
        if job["url"] in seen:
            continue
        seen.add(job["url"])
        result.append(job)
    return result


def fetch(url: str) -> str:
    request = Request(url, headers={"User-Agent": "auto-job-community-source/1.0", "Accept": "text/plain,text/markdown,text/html"})
    with urlopen(request, timeout=20) as response:
        return response.read().decode("utf-8", errors="replace")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--format", choices=("html", "markdown"), required=True)
    args = parser.parse_args(argv)
    try:
        document = fetch(args.url)
        jobs = parse_html_jobs(document, args.url) if args.format == "html" else parse_markdown_jobs(document, args.url)
    except Exception as exc:  # Career-Ops records the parser failure as a source error.
        print(f"community source fetch failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(jobs, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
