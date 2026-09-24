"""Collect JavaScript assets from a URL or the local filesystem.

A URL that is itself a `.js` file is fetched directly; an HTML page is scanned
for `<script src>` and `modulepreload` links, which are downloaded. A local path
may be a single file or a directory tree. Each returned Asset carries a `fetch`
callback so source maps referenced relative to it can be resolved the same way,
whether it came from the web or from disk.
"""
from __future__ import annotations

import re
import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import httpx

_SCRIPT_SRC = re.compile(r"<script[^>]+\bsrc=[\"']([^\"']+)[\"']", re.I)
_MODULEPRELOAD = re.compile(r"<link[^>]+rel=[\"']modulepreload[\"'][^>]+href=[\"']([^\"']+)[\"']", re.I)
_JS_SUFFIXES = (".js", ".mjs", ".cjs")
_SOURCE_SUFFIXES = _JS_SUFFIXES + (".ts", ".tsx", ".jsx")
_UA = "jsrecon/0.1 (+https://github.com/web3daemon/jsrecon)"
MAX_ASSETS = 60


@dataclass
class Asset:
    label: str
    text: str
    map_base: str                       # base for resolving a relative sourceMappingURL
    fetch: Callable[[str], str | None]  # resolver for that asset's source map


def is_url(target: str) -> bool:
    return target.startswith(("http://", "https://"))


class Loader:
    def __init__(self, timeout: float = 20.0, headers: dict | None = None):
        self.client = httpx.Client(
            follow_redirects=True, timeout=timeout,
            headers={"User-Agent": _UA, **(headers or {})},
        )

    def close(self) -> None:
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def _text(self, url: str) -> str | None:
        try:
            r = self.client.get(url)
        except httpx.HTTPError:
            return None
        return r.text if r.status_code == 200 else None

    def collect(self, target: str) -> list[Asset]:
        return self._collect_url(target) if is_url(target) else self._collect_local(target)

    def _collect_url(self, target: str) -> list[Asset]:
        try:
            resp = self.client.get(target)
        except httpx.HTTPError as e:
            raise RuntimeError(f"cannot fetch {target}: {e}") from e
        ctype = resp.headers.get("content-type", "")
        looks_js = target.split("?")[0].endswith(_JS_SUFFIXES) or "javascript" in ctype
        if looks_js:
            return [Asset(target, resp.text, target, self._text)]

        refs = _SCRIPT_SRC.findall(resp.text) + _MODULEPRELOAD.findall(resp.text)
        seen, assets = set(), []
        for ref in refs:
            url = urllib.parse.urljoin(target, ref)
            if not url.split("?")[0].endswith(_JS_SUFFIXES) or url in seen:
                continue
            seen.add(url)
            text = self._text(url)
            if text is not None:
                assets.append(Asset(url, text, url, self._text))
            if len(assets) >= MAX_ASSETS:
                break
        return assets

    def _collect_local(self, target: str) -> list[Asset]:
        p = Path(target)
        if not p.exists():
            raise RuntimeError(f"path not found: {target}")
        files = sorted(f for f in p.rglob("*") if f.suffix in _SOURCE_SUFFIXES) if p.is_dir() else [p]
        assets = []
        for f in files[:MAX_ASSETS]:
            assets.append(Asset(str(f), f.read_text(encoding="utf-8", errors="replace"), "", _local_fetch(f.parent)))
        return assets


def _local_fetch(base: Path) -> Callable[[str], str | None]:
    def read(ref: str) -> str | None:
        candidate = base / ref
        try:
            return candidate.read_text(encoding="utf-8", errors="replace") if candidate.is_file() else None
        except OSError:
            return None
    return read
