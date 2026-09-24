"""Flag secrets that should not ship in a client-side bundle.

This is a defensive audit for your own (or in-scope) bundles: a private key in
front-end JavaScript is downloadable by anyone, so this list is deliberately
narrow — high-risk *server* credentials, not the publishable keys (Stripe
`pk_`, Google Maps `AIza…`) that are meant to live in the client. Values are
masked in output; jsrecon never stores or transmits them.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from ..parse import Str

# (label, severity, compiled pattern). Severity: "high" = server credential.
_PATTERNS = [
    ("AWS access key id", "high", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("AWS secret access key", "high", re.compile(r"\baws_secret[^\"']{0,20}[:=]\s*['\"][0-9A-Za-z/+]{40}['\"]")),
    ("GitHub token", "high", re.compile(r"\bgh[pousr]_[0-9A-Za-z]{36,}\b")),
    ("Slack token", "high", re.compile(r"\bxox[baprs]-[0-9A-Za-z-]{10,}\b")),
    ("Stripe secret key", "high", re.compile(r"\bsk_live_[0-9A-Za-z]{24,}\b")),
    ("Google service private key", "high", re.compile(r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----")),
    ("Twilio account SID", "medium", re.compile(r"\bAC[0-9a-f]{32}\b")),
    ("Generic secret assignment", "low", re.compile(r"(?i)\b(?:api|secret|private|access)[_-]?(?:key|token|secret)\b\s*[:=]\s*['\"][0-9A-Za-z._\-]{16,}['\"]")),
]


@dataclass(frozen=True)
class Secret:
    label: str
    severity: str
    preview: str
    line: int


def _mask(match: str) -> str:
    match = match.strip("'\"")
    if len(match) <= 10:
        return match[:2] + "…"
    return f"{match[:4]}…{match[-2:]} ({len(match)} chars)"


def find(strings: list[Str]) -> list[Secret]:
    out: list[Secret] = []
    for s in strings:
        for label, sev, pat in _PATTERNS:
            m = pat.search(s.value)
            if m:
                out.append(Secret(label, sev, _mask(m.group(0)), s.line))
    return out
