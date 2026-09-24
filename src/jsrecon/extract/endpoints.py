"""Pull HTTP endpoints out of parsed JavaScript.

Two confidence levels:
  * `call`    — the string is the first argument of an HTTP client call
                (fetch/axios/ky/$.ajax/…). High confidence, method known.
  * `literal` — a bare string that looks like a URL or an API path. A candidate.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from ..parse import Call, Str

VERBS = ("get", "post", "put", "delete", "patch", "head", "options")

# callee (lower-cased) → HTTP client we recognise
_CLIENT_TAILS = ("fetch", "axios", "ky", "got", "superagent", "request", "$http", "httpclient")
_ASSET_RE = re.compile(r"\.(js|mjs|cjs|css|map|png|jpe?g|gif|svg|webp|ico|woff2?|ttf|eot|mp4|webm|wasm)(\?|#|$)", re.I)
_ABS_RE = re.compile(r"^https?://[^\s\"'<>]+$", re.I)
_PATH_RE = re.compile(r"^/[A-Za-z0-9._~%\-][^\s\"'<>]*$")
_API_HINT = re.compile(r"(/api\b|/v\d+\b|/graphql\b|/rest\b|/rpc\b|/oauth\b|/auth\b|/token\b|/users?\b|/account\b|/orders?\b|/login\b|/query\b)", re.I)


@dataclass(frozen=True)
class Endpoint:
    method: str          # "GET", "POST", … or "" for a bare literal
    url: str
    kind: str            # "call" | "literal"
    line: int


def _looks_like_url(s: str) -> bool:
    if not s or len(s) > 300 or " " in s or "\n" in s:
        return False
    if _ASSET_RE.search(s):
        return False
    return bool(_ABS_RE.match(s) or _PATH_RE.match(s))


def _method_from_callee(callee: str) -> str | None:
    low = callee.lower()
    tail = low.rsplit(".", 1)[-1]
    if tail in VERBS and any(t in low for t in _CLIENT_TAILS + ("api", "http", "client", "$", "service", "req")):
        return tail.upper()
    if low.endswith("fetch") or low.endswith("axios") or low == "axios" or low.endswith(".ajax") or low.endswith("request"):
        return "GET"
    if low.endswith(".open"):  # XMLHttpRequest#open(method, url) — method is arg 0
        return "GET"
    return None


def from_calls(calls: list[Call]) -> list[Endpoint]:
    out = []
    for c in calls:
        if not c.arg or not _looks_like_url(c.arg):
            continue
        method = _method_from_callee(c.callee)
        if method is None:
            continue
        out.append(Endpoint(method, c.arg, "call", c.line))
    return out


def from_literals(strings: list[Str]) -> list[Endpoint]:
    out = []
    for s in strings:
        v = s.value
        if not _looks_like_url(v):
            continue
        # a path literal is only interesting if it smells like an API route
        if _PATH_RE.match(v) and not (_API_HINT.search(v) or v.count("/") >= 2):
            continue
        out.append(Endpoint("", v, "literal", s.line))
    return out
