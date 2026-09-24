"""Find client-side routes (the app's own pages, not its API).

Router configs and JSX give these away with a `path:` key or a `<Route path=…>`
attribute. Kept separate from API endpoints — these are UI routes, useful for
mapping the surface of a single-page app.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

_ROUTE_RES = [
    re.compile(r"""["']?path["']?\s*:\s*["'](/[^"']*)["']"""),   # { path: "/x" }
    re.compile(r"""<Route\b[^>]*\bpath=["'](/[^"']*)["']"""),     # <Route path="/x">
]


@dataclass(frozen=True)
class Route:
    path: str
    line: int


def find(code: str) -> list[Route]:
    seen: dict[str, Route] = {}
    for rx in _ROUTE_RES:
        for m in rx.finditer(code):
            path = m.group(1)
            if "http" in path or len(path) > 200 or path in seen:
                continue
            line = code.count("\n", 0, m.start()) + 1
            seen[path] = Route(path, line)
    return list(seen.values())
