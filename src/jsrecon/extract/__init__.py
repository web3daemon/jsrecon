"""Analysis models and the per-file / per-run aggregators."""
from __future__ import annotations

import re
from dataclasses import dataclass, field, replace

from ..parse import lang_for, parse
from . import endpoints, graphql, routes, secrets
from .endpoints import Endpoint
from .graphql import GraphQLOp
from .routes import Route
from .secrets import Secret


@dataclass
class Analysis:
    endpoints: list[Endpoint] = field(default_factory=list)
    graphql: list[GraphQLOp] = field(default_factory=list)
    routes: list[Route] = field(default_factory=list)
    secrets: list[Secret] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)   # asset labels that were parsed

    def merge(self, other: Analysis) -> None:
        self.endpoints += other.endpoints
        self.graphql += other.graphql
        self.routes += other.routes
        self.secrets += other.secrets
        self.sources += other.sources

    def dedupe(self) -> Analysis:
        """Collapse duplicates. For equal findings the first one seen wins, so
        callers merge recovered original sources before the minified bundle and
        a finding points at `src/api/orders.ts:14`, not `app.js:1`."""
        # a `call` endpoint outranks a bare `literal` for the same URL
        # `/orders/{id}` from the source and `/orders/{param}` from the bundle
        # are one endpoint; placeholders are compared by position, not name
        best: dict[tuple[str, str], Endpoint] = {}
        for e in self.endpoints:
            key = (e.method, _shape(e.url))
            if key not in best or (e.kind == "call" and best[key].kind == "literal"):
                best[key] = e
        # drop literal duplicates already covered by a call to the same URL,
        # or by a client-side route of the same path (those are UI, not API)
        self.routes = sorted(_first(self.routes, lambda r: r.path), key=lambda r: r.path)
        covered = {_shape(e.url) for e in best.values() if e.kind == "call"} | {r.path for r in self.routes}
        self.endpoints = sorted(
            (e for e in best.values() if not (e.kind == "literal" and _shape(e.url) in covered)),
            key=lambda e: (e.kind != "call", e.url),
        )
        self.graphql = sorted(_first(self.graphql, lambda g: (g.operation, g.name)),
                              key=lambda g: (g.operation, g.name))
        self.secrets = _first(self.secrets, lambda s: (s.label, s.preview))
        self.sources = sorted(set(self.sources))
        return self


_PARAM = re.compile(r"\{[^{}/]*\}")


def _shape(url: str) -> str:
    return _PARAM.sub("{}", url)


def _first(items, key) -> list:
    seen: dict = {}
    for it in items:
        seen.setdefault(key(it), it)
    return list(seen.values())


def analyze_code(code: str, label: str = "<code>") -> Analysis:
    strings, calls = parse(code, lang_for(label))

    def tag(found):
        return [replace(x, source=label) for x in found]

    return Analysis(
        endpoints=tag(endpoints.from_calls(calls) + endpoints.from_literals(strings)),
        graphql=tag(graphql.find(strings, calls)),
        routes=tag(routes.find(code)),
        secrets=tag(secrets.find(strings)),
        sources=[label],
    )
