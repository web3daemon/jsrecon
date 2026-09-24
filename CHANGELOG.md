# Changelog

## 0.2.0 — 2026-09-25

- **Path and query parameters.** Template paths keep their shape: `` `/orders/${id}/refund` ``
  becomes `/orders/{id}/refund` instead of being cut to `/orders/`; the OpenAPI skeleton gets
  `path` and `query` parameters. Minifier names (`${t}`) become `{param}`.
- **URLs split across `+`** resolve: `"/api/" + "orders"` → `/api/orders`, `"/users/" + id` →
  `/users/{id}`; the halves are no longer reported as endpoints of their own.
- **Every finding says where it came from** — `file:line`, in the original source when a source
  map is available (originals are analysed before the bundle and win on a tie).
- **Minified clients.** `s.get("/api/orders")` is recognised even after the bundler renamed the
  client; an API-shaped argument of an unknown call is kept as a candidate instead of dropped.
- `fetch(url, { method })` and `XMLHttpRequest.open(method, url)` resolve the method.
- Client-side routes from router tables and `<Route path>`.
- `--json` writes only JSON to stdout (the table goes to stderr), so it pipes into `jq`.
- The run summary shows source maps unpacked, files parsed and elapsed time.
- Doesn't crash on legacy Windows consoles that can't encode a character.
- Demo shop in `examples/shop`, README demo recorded from a real run (`scripts/gen_demo.py`).

## 0.1.0

- First cut: fetch a page's bundles or a local build, unpack source maps, parse with
  tree-sitter, report endpoints, GraphQL operations and client-leaked secrets as a table,
  JSON, Markdown and an OpenAPI 3.1 skeleton.
