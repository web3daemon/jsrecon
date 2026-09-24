from pathlib import Path

from jsrecon import sourcemaps
from jsrecon.extract import analyze_code

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


def test_method_from_fetch_options():
    # fetch("/v1/session", { method: "POST" }) must resolve to POST, not GET
    assert ("POST", "/v1/session") in _endpoints(APP)


def test_xhr_open_method_and_url():
    assert ("GET", "/api/health") in _endpoints(APP)


def test_client_routes():
    a = analyze_code(APP, "app.js")
    a.dedupe()
    paths = {r.path for r in a.routes}
    assert {"/dashboard", "/login"} <= paths


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
    assert ("DELETE", "/api/users/{id}") in eps


def test_path_safety_blocks_traversal():
    assert sourcemaps._safe("webpack://app/../../etc/passwd") == "app/etc/passwd"
    assert not sourcemaps._safe("/../../secret").startswith("/")


def test_template_path_becomes_parameter():
    code = "api.post(`/orders/${order.id}/refund`, {}); api.get(`/search?q=${query}&page=${p}`)"
    assert ("POST", "/orders/{id}/refund") in _endpoints(code)
    assert ("GET", "/search?q={query}&page={param}") in _endpoints(code)


def test_template_without_static_prefix_is_skipped():
    assert not _endpoints("api.get(`${base}/users`)")


def test_minified_client_verb_call():
    # the bundler renamed `api` to `s`; the verb and the API-shaped path remain
    assert ("DELETE", "/api/orders/{param}") in _endpoints('s.delete(`/api/orders/${t}`)')
    # a verb on a non-API string is not an endpoint
    assert not _endpoints('m.get("/")')


def test_original_source_wins_over_bundle():
    a = analyze_code("api.get(`/orders/${id}`)", "src/api/orders.ts")
    a.merge(analyze_code("s.get(`/orders/${t}`)", "http://x/assets/main.js"))
    a.dedupe()
    [e] = a.endpoints
    assert (e.url, e.source) == ("/orders/{id}", "src/api/orders.ts")


def test_openapi_parameters():
    from jsrecon import report
    a = analyze_code("api.get(`/orders/${id}?expand=${fields}`)", "src/a.ts")
    a.dedupe()
    op = report.to_openapi(a, "t")["paths"]["/orders/{id}"]["get"]
    assert {(p["name"], p["in"]) for p in op["parameters"]} == {("id", "path"), ("expand", "query")}


def test_unknown_callee_keeps_api_argument_as_candidate():
    # `const r = window.fetch; r("/api/orders")` — the callee is opaque, the path isn't
    assert ("", "/api/orders") in _endpoints('r("/api/orders")')
    assert not _endpoints('t("some.i18n.key")')


def test_string_concatenation_resolves():
    # the minifier split the URL across a `+`; a regex only sees "/api/"
    assert ("GET", "/api/orders") in _endpoints('e.get("/api/"+"orders")')
    assert ("", "/api/users/{id}") in _endpoints('const u = "/api/users/" + id;')
    # the halves are not reported as endpoints of their own
    assert ("", "/api/") not in _endpoints('e.get("/api/"+"orders")')
    # no static anchor on the left: no call, the right half stays a bare candidate
    assert _endpoints("api.get(base + '/users')") == {("", "/users")}
