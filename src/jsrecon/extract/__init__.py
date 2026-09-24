"""Analysis models and the per-file / per-run aggregators."""
from __future__ import annotations

from dataclasses import dataclass, field

from ..parse import lang_for, parse
from . import endpoints, graphql, secrets
from .endpoints import Endpoint
from .graphql import GraphQLOp
from .secrets import Secret


@dataclass
class Analysis:
    endpoints: list[Endpoint] = field(default_factory=list)
    graphql: list[GraphQLOp] = field(default_factory=list)
    secrets: list[Secret] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)   # asset labels that were parsed

    def merge(self, other: "Analysis") -> None:
        self.endpoints += other.endpoints
        self.graphql += other.graphql
        self.secrets += other.secrets
        self.sources += other.sources

    def dedupe(self) -> "Analysis":
        # a `call` endpoint outranks a bare `literal` for the same URL
        best: dict[tuple[str, str], Endpoint] = {}
        for e in self.endpoints:
            key = (e.method, e.url)
            if key not in best or (e.kind == "call" and best[key].kind == "literal"):
                best[key] = e
        # drop literal duplicates already covered by a call to the same URL
        call_urls = {e.url for e in best.values() if e.kind == "call"}
        self.endpoints = sorted(
            (e for e in best.values() if not (e.kind == "literal" and e.url in call_urls)),
            key=lambda e: (e.kind != "call", e.url),
        )
        self.graphql = sorted(set(self.graphql), key=lambda g: (g.operation, g.name))
        self.secrets = list({(s.label, s.preview, s.line): s for s in self.secrets}.values())
        self.sources = sorted(set(self.sources))
        return self


def analyze_code(code: str, label: str = "<code>") -> Analysis:
    strings, calls = parse(code, lang_for(label))
    return Analysis(
        endpoints=endpoints.from_calls(calls) + endpoints.from_literals(strings),
        graphql=graphql.find(strings, calls),
        secrets=secrets.find(strings),
        sources=[label],
    )
