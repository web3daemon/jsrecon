"""Turn a `.map` file back into the original source tree.

When a bundle ships `sourcesContent`, the original files are literally inside the
map — no VLQ decoding needed to recover them. That is often the richest input
jsrecon has: readable pre-minification code with real names and comments.
"""
from __future__ import annotations

import base64
import json
import posixpath
import re
import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

_SM_RE = re.compile(r"//[#@]\s*sourceMappingURL=(\S+)")


@dataclass
class SourceMap:
    sources: list[str]
    contents: list[str | None]

    def originals(self) -> list[tuple[str, str]]:
        out = []
        for name, content in zip(self.sources, self.contents):
            if content is not None:
                out.append((name, content))
        return out


def map_url(code: str) -> str | None:
    matches = _SM_RE.findall(code)
    return matches[-1] if matches else None


def load(code: str, asset_url: str, fetch: Callable[[str], str | None]) -> SourceMap | None:
    """Locate and parse the source map referenced by `code`, if any."""
    ref = map_url(code)
    if not ref:
        return None
    if ref.startswith("data:"):
        header, _, payload = ref.partition(",")
        raw = base64.b64decode(payload).decode("utf-8", "replace") if ";base64" in header else urllib.parse.unquote(payload)
    else:
        target = ref if ref.startswith(("http://", "https://")) else urllib.parse.urljoin(asset_url, ref)
        raw = fetch(target)
        if raw is None:
            return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    sources = data.get("sources") or []
    contents = data.get("sourcesContent") or [None] * len(sources)
    contents += [None] * (len(sources) - len(contents))
    return SourceMap(sources, contents)


def _safe(name: str) -> str:
    """Map a source path to a tree path that can't escape the output dir."""
    name = name.split("?", 1)[0].split("#", 1)[0]
    name = re.sub(r"^\w+://", "", name)                 # webpack://, file://
    name = name.replace("\\", "/").lstrip("/")
    parts = [p for p in name.split("/") if p not in ("", ".", "..")]
    parts = [re.sub(r'[<>:"|?*]', "_", p) for p in parts]
    return posixpath.join(*parts) if parts else "unnamed"


def write_originals(sm: SourceMap, out_dir: Path) -> list[Path]:
    written = []
    for name, content in sm.originals():
        dest = out_dir / _safe(name)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")
        written.append(dest)
    return written
