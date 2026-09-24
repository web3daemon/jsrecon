from pathlib import Path

from jsrecon.extract import analyze_code
from jsrecon import sourcemaps

FIX = Path(__file__).parent / "fixtures"
APP = (FIX / "app.js").read_text(encoding="utf-8")


def _endpoints(code, label="app.js"):
    a = analyze_code(code, label)
    a.dedupe()
    return {(e.method, e.url) for e in a.endpoints}


def test_call_endpoint_with_method():
    eps = _endpoints(APP)
    assert ("POST", "/api/orders") in eps
    assert ("GET", "/api/users") in eps


def test_absolute_url_literal():
    eps = _endpoints(APP)
    assert any(url == "https://api.example.com/v2" for _, url in eps)


def test_graphql_operation():
    a = analyze_code(APP, "app.js")
    a.dedupe()
    assert any(g.operation == "query" and g.name == "GetUser" for g in a.graphql)


def test_client_secret_flagged():
    a = analyze_code(APP, "app.js")
    assert any("AWS" in s.label for s in a.secrets)
    # value must be masked, never echoed in full
    assert all("AKIAIOSFODNN7EXAMPLE" != s.preview for s in a.secrets)


def test_sourcemap_recovers_originals_and_endpoints():
    sm = sourcemaps.load(APP, "", lambda ref: (FIX / ref).read_text(encoding="utf-8"))
    assert sm is not None
    originals = sm.originals()
    assert originals and originals[0][0].endswith("api.ts")
    eps = set()
    for name, content in originals:
        a = analyze_code(content, name)
        a.dedupe()
        eps |= {(e.method, e.url) for e in a.endpoints}
    assert ("GET", "/api/profile") in eps
    assert ("DELETE", "/api/users/") in eps


def test_path_safety_blocks_traversal():
    assert sourcemaps._safe("webpack://app/../../etc/passwd") == "app/etc/passwd"
    assert not sourcemaps._safe("/../../secret").startswith("/")
