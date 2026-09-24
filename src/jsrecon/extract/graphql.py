r"""Find GraphQL operations in parsed JavaScript.

Operations live in two places: inside ``gql`…` `` / ``graphql`…` `` tagged
templates, and inside plain strings beginning with query/mutation/subscription.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from ..parse import Call, Str

_OP_RE = re.compile(r"\b(query|mutation|subscription)\b(?:\s+([A-Za-z_]\w*))?\s*[({]")


@dataclass(frozen=True)
class GraphQLOp:
    operation: str       # "query" | "mutation" | "subscription"
    name: str            # operation name or "(anonymous)"
    line: int
    source: str = ""     # file the finding came from (bundle or original source)


def _scan(text: str, line: int) -> list[GraphQLOp]:
    found = []
    for m in _OP_RE.finditer(text):
        found.append(GraphQLOp(m.group(1), m.group(2) or "(anonymous)", line))
    return found


def find(strings: list[Str], calls: list[Call]) -> list[GraphQLOp]:
    out: list[GraphQLOp] = []
    for s in strings:
        if "query" in s.value or "mutation" in s.value or "subscription" in s.value:
            out.extend(_scan(s.value, s.line))
    for c in calls:
        if c.arg and c.callee.lower().rsplit(".", 1)[-1] in ("gql", "graphql") :
            out.extend(_scan(c.arg, c.line))
    return out
