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
    source: str = ""     # file the finding came from (bundle or original source)


def _looks_like_url(s: str) -> bool:
    if not s or len(s) > 300 or " " in s or "\n" in s:
        return False
    if _ASSET_RE.search(s):
        return False
    return bool(_ABS_RE.match(s) or _PATH_RE.match(s))


_VERBS_UP = tuple(v.upper() for v in VERBS)


def _method_from_callee(callee: str) -> str | None:
    low = callee.lower()
    tail = low.rsplit(".", 1)[-1]
    if tail in VERBS and any(t in low for t in _CLIENT_TAILS + ("api", "http", "client", "$", "service", "req")):
        return tail.upper()
    if low.endswith("fetch") or low.endswith("axios") or low == "axios" or low.endswith(".ajax") or low.endswith("request"):
        return "GET"
    return None


def from_calls(calls: list[Call]) -> list[Endpoint]:
    out = []
    for c in calls:
        tail = c.callee.lower().rsplit(".", 1)[-1]
        # XMLHttpRequest#open(method, url)
        if tail == "open" and len(c.args) >= 2 and c.args[0].upper() in _VERBS_UP and _looks_like_url(c.args[1]):
            out.append(Endpoint(c.args[0].upper(), c.args[1], "call", c.line))
            continue
        url = next((a for a in c.args if _looks_like_url(a)), None)
        if url is None:
            continue
        method = _method_from_callee(c.callee)
        if method is None and tail in VERBS and _api_shaped(url):
            # minified client: `s.get("/api/orders")` — the object lost its name,
            # but a verb method on an API-shaped path is still an HTTP call
            method = tail.upper()
        if method is None:
            # unknown callee (a renamed fetch, a wrapper): keep an API-shaped
            # argument as a candidate rather than dropping it
            if _api_shaped(url):
                out.append(Endpoint("", url, "literal", c.line))
            continue
        if c.method_opt:                      # fetch(url, { method: "POST" }) wins
            method = c.method_opt.upper()
        out.append(Endpoint(method, url, "call", c.line))
    return out


def _api_shaped(v: str) -> bool:
    return bool(_ABS_RE.match(v) or _API_HINT.search(v))


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
