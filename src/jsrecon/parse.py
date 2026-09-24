"""Thin wrapper over tree-sitter for JavaScript/TypeScript.

Everything downstream works on the syntax tree, so a renamed variable or a
string split across a `+` never fools us the way a pure-regex scanner is fooled.
When the grammar can't be loaded we fall back to a regex tokenizer that yields
the same shapes, so the tool still runs (with lower precision).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

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


def placeholder(expr: str, taken: set[str]) -> str:
    """`${order.id}` → `{id}`: a path-parameter name for an interpolation.

    One- and two-letter names (other than `id`) are almost always the
    minifier's, so they become `{param}`; repeats in the same string get a
    suffix to stay unique."""
    m = re.search(r"([A-Za-z_$][\w$]*)\s*$", expr.strip())
    name = m.group(1).lstrip("$") if m else ""
    if len(name) < 3 and name != "id":
        name = "param"
    base, i = name, 2
    while name in taken:
        name, i = f"{base}{i}", i + 1
    taken.add(name)
    return "{" + name + "}"


def _string_literal(node, src: bytes) -> str | None:
    """The static value of a string / template node.

    Interpolations become `{name}` placeholders (`/orders/${id}/refund` →
    `/orders/{id}/refund`). A template that *starts* with one has no static
    anchor to resolve (`${base}/x`), so it yields ""."""
    if node.type == "string":
        raw = _node_text(node, src)
        return raw[1:-1] if len(raw) >= 2 else ""
    if node.type == "template_string":
        parts = [c for c in node.children if c.type not in ("`",)]
        if parts and parts[0].type == "template_substitution":
            return ""
        taken: set[str] = set()
        out = []
        for c in parts:
            if c.type == "template_substitution":
                out.append(placeholder(_node_text(c, src)[2:-1], taken))
            else:
                out.append(_node_text(c, src))
        return "".join(out)
    return None


def _concat(node, src: bytes, taken: set[str]) -> str | None:
    """`"/api/" + "orders"` → "/api/orders"; `"/users/" + id` → "/users/{id}".

    Resolves a `+` chain whose leftmost operand is a string: the minifier's
    favourite way to split a URL. Non-string operands become placeholders. A
    chain that starts with a variable (`base + "/x"`) has no anchor → None."""
    t = node.type
    if t in ("string", "template_string"):
        return _string_literal(node, src)
    if t == "parenthesized_expression" and node.named_children:
        return _concat(node.named_children[0], src, taken)
    if t == "binary_expression":
        op = node.child_by_field_name("operator")
        left, right = node.child_by_field_name("left"), node.child_by_field_name("right")
        if op is None or _node_text(op, src) != "+" or left is None or right is None:
            return None
        head = _concat(left, src, taken)
        if head is None:
            return None
        tail = _concat(right, src, taken)
        return head + (tail if tail is not None else placeholder(_node_text(right, src), taken))
    return None


def _value(node, src: bytes) -> str | None:
    """The static value of a string, template, or `+` chain of them."""
    if node.type == "binary_expression":
        return _concat(node, src, set())
    return _string_literal(node, src)


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
    stack = [tree.root_node]
    while stack:
        node = stack.pop()
        if node.type in ("string", "template_string", "binary_expression"):
            val = _value(node, src)
            if val is not None:
                # a call argument is recorded by the call handler, with its method
                parent = node.parent
                if parent is None or parent.type != "arguments":
                    strings.append(Str(val, node.start_point[0] + 1))
                if node.type == "binary_expression":
                    continue          # its pieces are part of this value, not strings of their own
        elif node.type == "call_expression":
            fn = node.child_by_field_name("function")
            arg_node = node.child_by_field_name("arguments")
            callee = _node_text(fn, src) if fn is not None else ""
            args: list[str] = []
            method_opt = None
            if arg_node is not None:
                for child in arg_node.named_children:
                    v = _value(child, src)
                    if v is not None:
                        args.append(v)
                    elif child.type == "object":
                        method_opt = method_opt or _object_method(child, src)
            calls.append(Call(callee, args, method_opt, node.start_point[0] + 1))
        stack.extend(reversed(node.children))
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


_SUBST_RE = re.compile(r"\$\{([^}]*)\}")


def _template_value(raw: str) -> str:
    """Same placeholder rule as the tree-sitter path, for the regex fallback."""
    if raw.startswith("${"):
        return ""
    taken: set[str] = set()
    return _SUBST_RE.sub(lambda m: placeholder(m.group(1), taken), raw)


def _parse_regex(code: str) -> tuple[list[Str], list[Call]]:
    strings = [Str(_template_value(m.group(2)), _line_of(code, m.start())) for m in _STR_RE.finditer(code)]
    calls = [Call(m.group(1), [_template_value(m.group(3))], None, _line_of(code, m.start())) for m in _CALL_RE.finditer(code)]
    return strings, calls
