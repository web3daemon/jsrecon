"""Thin wrapper over tree-sitter for JavaScript/TypeScript.

Everything downstream works on the syntax tree, so a renamed variable or a
string split across a `+` never fools us the way a pure-regex scanner is fooled.
When the grammar can't be loaded we fall back to a regex tokenizer that yields
the same shapes, so the tool still runs (with lower precision).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterator

try:
    from tree_sitter_language_pack import get_parser

    _PARSERS = {}

    def _parser(lang: str):
        if lang not in _PARSERS:
            _PARSERS[lang] = get_parser(lang)
        return _PARSERS[lang]

    HAVE_TS = True
except Exception:  # pragma: no cover - only when grammars are missing
    HAVE_TS = False


def lang_for(path: str) -> str:
    p = path.lower()
    if p.endswith((".ts", ".mts", ".cts")):
        return "typescript"
    if p.endswith((".tsx",)):
        return "tsx"
    return "javascript"


@dataclass
class Str:
    """A string the code actually builds, plus the line it sits on."""

    value: str
    line: int


@dataclass
class Call:
    """A function call: callee text, its string arguments in order, and — when an
    options object is passed — the `method:` found inside it (for `fetch`)."""

    callee: str
    args: list[str]
    method_opt: str | None
    line: int

    @property
    def arg(self) -> str | None:
        return self.args[0] if self.args else None


def _node_text(node, src: bytes) -> str:
    return src[node.start_byte : node.end_byte].decode("utf-8", "replace")


def _string_literal(node, src: bytes) -> str | None:
    """The static value of a string / template node, cut at the first ${…}."""
    if node.type == "string":
        raw = _node_text(node, src)
        return raw[1:-1] if len(raw) >= 2 else ""
    if node.type == "template_string":
        raw = _node_text(node, src)[1:-1]
        return raw.split("${", 1)[0]
    return None


def _walk(node) -> Iterator:
    stack = [node]
    while stack:
        n = stack.pop()
        yield n
        stack.extend(reversed(n.children))


def parse(code: str, lang: str = "javascript") -> tuple[list[Str], list[Call]]:
    """Return (strings, calls) found in `code`."""
    if HAVE_TS:
        try:
            return _parse_ts(code, lang)
        except Exception:
            pass
    return _parse_regex(code)


def _parse_ts(code: str, lang: str) -> tuple[list[Str], list[Call]]:
    src = code.encode("utf-8")
    tree = _parser(lang).parse(src)
    strings: list[Str] = []
    calls: list[Call] = []
    for node in _walk(tree.root_node):
        if node.type in ("string", "template_string"):
            # skip strings that are themselves call arguments; the call handler
            # records those with their method, avoiding duplicates
            parent = node.parent
            if parent is not None and parent.type == "arguments":
                continue
            val = _string_literal(node, src)
            if val is not None:
                strings.append(Str(val, node.start_point[0] + 1))
        elif node.type == "call_expression":
            fn = node.child_by_field_name("function")
            arg_node = node.child_by_field_name("arguments")
            callee = _node_text(fn, src) if fn is not None else ""
            args: list[str] = []
            method_opt = None
            if arg_node is not None:
                for child in arg_node.named_children:
                    v = _string_literal(child, src)
                    if v is not None:
                        args.append(v)
                    elif child.type == "object":
                        method_opt = method_opt or _object_method(child, src)
            calls.append(Call(callee, args, method_opt, node.start_point[0] + 1))
    return strings, calls


def _object_method(obj, src: bytes) -> str | None:
    """The value of a `method:` property inside an object literal, if any."""
    for pair in obj.named_children:
        if pair.type != "pair":
            continue
        key, value = pair.child_by_field_name("key"), pair.child_by_field_name("value")
        if key is None or value is None:
            continue
        if _node_text(key, src).strip("'\"") .lower() == "method":
            return _string_literal(value, src)
    return None


# --- regex fallback -------------------------------------------------------
_STR_RE = re.compile(r"""(['"`])((?:\\.|(?!\1).)*?)\1""")
_CALL_RE = re.compile(r"""([A-Za-z_$][\w$.]*)\s*\(\s*(['"`])((?:\\.|(?!\2).)*?)\2""")


def _line_of(code: str, pos: int) -> int:
    return code.count("\n", 0, pos) + 1


def _parse_regex(code: str) -> tuple[list[Str], list[Call]]:
    strings = [Str(m.group(2).split("${", 1)[0], _line_of(code, m.start())) for m in _STR_RE.finditer(code)]
    calls = [Call(m.group(1), [m.group(3).split("${", 1)[0]], None, _line_of(code, m.start())) for m in _CALL_RE.finditer(code)]
    return strings, calls
