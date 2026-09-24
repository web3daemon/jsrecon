"""Render an Analysis as JSON, Markdown, or an OpenAPI 3.1 skeleton."""
from __future__ import annotations

import json
import re
import urllib.parse
from collections import defaultdict

from .extract import Analysis


def where(source: str, line: int) -> str:
    """`src/api/orders.ts:14` — a short location for tables and reports."""
    src = source.split("?", 1)[0].replace("\\", "/")
    if "://" in src:                                   # a fetched bundle: keep the file name
        src = src.rstrip("/").rsplit("/", 1)[-1] or src
    elif not src.startswith("src/"):                   # a local path: keep the last two parts
        src = "/".join(src.split("/")[-2:])
    return f"{src}:{line}" if src else str(line)


def to_dict(a: Analysis, target: str) -> dict:
    return {
        "target": target,
        "sources_parsed": a.sources,
        "endpoints": [{"method": e.method or None, "url": e.url, "confidence": e.kind, "source": e.source, "line": e.line} for e in a.endpoints],
        "graphql": [{"operation": g.operation, "name": g.name, "source": g.source, "line": g.line} for g in a.graphql],
        "routes": [{"path": r.path, "source": r.source, "line": r.line} for r in a.routes],
        "secrets": [{"label": s.label, "severity": s.severity, "preview": s.preview, "source": s.source, "line": s.line} for s in a.secrets],
    }


def to_json(a: Analysis, target: str) -> str:
    return json.dumps(to_dict(a, target), indent=2, ensure_ascii=False)


def to_markdown(a: Analysis, target: str) -> str:
    lines = [f"# jsrecon — {target}", ""]
    lines.append(f"Parsed **{len(a.sources)}** source files · "
                 f"**{len(a.endpoints)}** endpoints · "
                 f"**{len(a.graphql)}** GraphQL ops · "
                 f"**{len(a.routes)}** routes · "
                 f"**{len(a.secrets)}** secret findings.\n")

    if a.endpoints:
        lines += ["## Endpoints", "", "| Method | URL | Confidence | Found in |", "|---|---|---|---|"]
        for e in a.endpoints:
            lines.append(f"| {e.method or '—'} | `{e.url}` | {e.kind} | `{where(e.source, e.line)}` |")
        lines.append("")
    if a.graphql:
        lines += ["## GraphQL", "", "| Operation | Name | Found in |", "|---|---|---|"]
        for g in a.graphql:
            lines.append(f"| {g.operation} | `{g.name}` | `{where(g.source, g.line)}` |")
        lines.append("")
    if a.routes:
        lines += ["## Client-side routes", "", "| Path | Found in |", "|---|---|"]
        for r in a.routes:
            lines.append(f"| `{r.path}` | `{where(r.source, r.line)}` |")
        lines.append("")
    if a.secrets:
        lines += ["## Secrets that should not ship to the client", "",
                  "| Severity | Kind | Preview | Found in |", "|---|---|---|---|"]
        for s in a.secrets:
            lines.append(f"| {s.severity} | {s.label} | `{s.preview}` | `{where(s.source, s.line)}` |")
        lines.append("")
    return "\n".join(lines)


_PARAM_RE = re.compile(r"\{([^{}/]+)\}")


def _parameters(path: str, query: str) -> list[dict]:
    params = [{"name": n, "in": "path", "required": True, "schema": {"type": "string"}}
              for n in _PARAM_RE.findall(path)]
    for key in urllib.parse.parse_qs(query, keep_blank_values=True):
        params.append({"name": key, "in": "query", "required": False, "schema": {"type": "string"}})
    return params


def to_openapi(a: Analysis, target: str) -> dict:
    """A best-effort OpenAPI 3.1 skeleton — a starting point, not a finished spec.

    `/orders/{id}` keeps its template as a path parameter; `?page={page}` turns
    into a query parameter."""
    servers: dict[str, None] = {}
    paths: dict[str, dict] = defaultdict(dict)
    for e in a.endpoints:
        parsed = urllib.parse.urlparse(e.url)
        if parsed.scheme:
            servers[f"{parsed.scheme}://{parsed.netloc}"] = None
        path = parsed.path or "/"
        if e.kind == "literal" and parsed.scheme and path == "/":
            continue                                  # a bare origin is a server, not an operation
        method = (e.method or "get").lower()
        op = {
            "summary": f"seen in client JS at {where(e.source, e.line)} ({e.kind})",
            "responses": {"200": {"description": "observed"}},
        }
        params = _parameters(path, parsed.query)
        if params:
            op["parameters"] = params
        paths[path].setdefault(method, op)
    return {
        "openapi": "3.1.0",
        "info": {"title": f"Reconstructed from {target}", "version": "0.0.0",
                 "description": "Skeleton inferred by jsrecon from client-side JavaScript. Verify before use."},
        "servers": [{"url": u} for u in servers],
        "paths": dict(paths),
    }
