<div align="center">

<img src="https://raw.githubusercontent.com/web3daemon/jsrecon/main/assets/logo.svg" alt="jsrecon" width="880">

### Point it at a web app. Get the API its JavaScript talks to.

jsrecon unpacks source maps, parses every bundle with a real JavaScript grammar and hands you
the endpoints, GraphQL operations, routes and leaked keys the front-end knows about —
as a table, JSON, Markdown and an OpenAPI 3.1 skeleton.

[![CI](https://github.com/web3daemon/jsrecon/actions/workflows/ci.yml/badge.svg)](https://github.com/web3daemon/jsrecon/actions/workflows/ci.yml)
[![Release v0.2.0](https://raw.githubusercontent.com/web3daemon/jsrecon/main/assets/badge-version.svg)](https://pypi.org/project/jsrecon/)
[![Python 3.10+](https://raw.githubusercontent.com/web3daemon/jsrecon/main/assets/badge-python.svg)](https://www.python.org/)
[![License MIT](https://raw.githubusercontent.com/web3daemon/jsrecon/main/assets/badge-license.svg)](https://github.com/web3daemon/jsrecon/blob/main/LICENSE)
[![Parser tree-sitter](https://raw.githubusercontent.com/web3daemon/jsrecon/main/assets/badge-parser.svg)](https://tree-sitter.github.io/)
[![Output OpenAPI 3.1](https://raw.githubusercontent.com/web3daemon/jsrecon/main/assets/badge-openapi.svg)](#output)

**English** · [Русский](https://github.com/web3daemon/jsrecon/blob/main/README.ru.md)

<br>

<img src="https://raw.githubusercontent.com/web3daemon/jsrecon/main/assets/demo.svg" alt="jsrecon demo: mapping the demo shop — endpoints, GraphQL, routes, a leaked key, recovered sources" width="100%">

[**Install**](#install) · [**Try it**](#try-it-in-30-seconds) · [**What it finds**](#what-it-finds) · [**Use**](#use) · [**Output**](#output) · [**How it works**](#how-it-works) · [**Intended use**](#intended-use) · [**Roadmap**](#roadmap)

</div>

## Install

```bash
pipx install jsrecon          # or: pip install jsrecon inside a venv
```

Python 3.10+. No config, no API keys, no browser.

## Try it in 30 seconds

The repo ships a small demo shop — TypeScript sources, bundled and minified with esbuild, with its
source map next to the bundle, exactly as a lot of production front-ends go out:

```bash
git clone https://github.com/web3daemon/jsrecon && cd jsrecon
python -m http.server 8080 -d examples/shop/dist      # in one terminal
jsrecon map http://localhost:8080 -o recon            # in another
```

That is the run in the demo above: 16 endpoints with their methods and path parameters,
4 GraphQL operations, 8 screens, one AWS key that should never have shipped — each one pointing at
the original file and line, `src/api/orders.ts:18`, not `main-RU4RXFFD.js:1`.

## Why

Grepping a minified bundle for `/api/` gives you noise: strings that were never URLs, and URLs
that were built with a `+` or a template, so the regex only sees half of them.

**jsrecon reads the code the way the engine does.** It parses every bundle with
[tree-sitter](https://tree-sitter.github.io/), so a URL split across a `+`
(`"/api/" + "orders"`), a minified `s.get(…)`, a method hidden in the options object
(`fetch(url, { method: "POST" })`) and a templated path (`` `/orders/${id}/refund` `` →
`/orders/{id}/refund`) all resolve.

**And when the bundle ships a source map, the original TypeScript is sitting right inside it.**
jsrecon writes that tree back to disk and reads *that* instead of the minified soup — real names,
real comments, real file layout. Every finding points at the original file and line.

## What it finds

| | |
|---|---|
| 🌐 **HTTP endpoints** | `fetch` / `axios` / `ky` / `$.ajax` / XHR calls with their **method**, plus API-shaped URL and path literals |
| 🧩 **Path & query parameters** | `` `/orders/${id}` `` → `/orders/{id}`, `?page=${page}` → a query parameter — straight into OpenAPI |
| 🧬 **GraphQL** | `query` / `mutation` / `subscription` operations, in `gql` tags and plain strings |
| 🗺 **Source maps → sources** | `sourcesContent` unpacked into the original file tree, then analysed first |
| 🧭 **Client-side routes** | router tables and `<Route path>` — every screen of the app before you click |
| 🔑 **Leaked server secrets** | a narrow, defensive scan for credentials that must never reach a browser — always masked |
| 📍 **Where it came from** | every finding carries `file:line`, in the original source when a map exists |
| 📤 **Reports** | live table, `findings.json`, `findings.md`, `openapi.json` and the `sources/` tree |

## Use

```bash
jsrecon map https://app.example.com              # crawl a page's <script> and modulepreload bundles
jsrecon map https://app.example.com/main.js      # one bundle
jsrecon map ./dist                               # a local build directory
jsrecon map ./dist -o recon                      # + write reports and recovered sources
jsrecon map ./app.min.js --json | jq '.endpoints'   # JSON to stdout
```

`jsrecon <target>` is shorthand for `jsrecon map <target>`.

| flag | |
|---|---|
| `-o, --out DIR` | write `findings.json`, `findings.md`, `openapi.json` and `sources/` into `DIR` |
| `--json` | print the findings as JSON to stdout (the table moves to stderr) |
| `--no-secrets` | skip the client-secret audit |
| `--timeout N` | HTTP timeout in seconds (default 20) |

## Output

`jsrecon map … -o recon` writes:

```
recon/
├── findings.json      every finding with method, confidence, source file and line
├── findings.md        the same as Markdown tables, ready for a ticket or a report
├── openapi.json       an OpenAPI 3.1 skeleton: paths, methods, path/query parameters
└── sources/           the original tree recovered from source maps
    └── src/api/orders.ts …
```

The OpenAPI file is a skeleton — paths and parameters, not request or response schemas. It's a
starting point for a client or for [httpcrabber](https://github.com/web3daemon/httpcrabber-client)'s
traffic-based spec, not a finished contract.

```json
"/orders/{id}/refund": {
  "post": {
    "summary": "seen in client JS at src/api/orders.ts:18 (call)",
    "parameters": [{ "name": "id", "in": "path", "required": true, "schema": { "type": "string" } }]
  }
}
```

## How it works

```
target ─► fetch ─► [bundles] ─┬─► source map? ─► original sources ─┐
 (URL, .js, ./dist)            │                                    ├─► tree-sitter ─► strings + calls
                               └────────────────────────────────────┘          │
                                                                 ┌──────────────┼─────────────┬──────────┐
                                                             endpoints       graphql        routes    secrets
                                                                 └──────────────┴──── dedupe ─┴──────────┘
                                                                                     │
                                                              table · json · md · openapi · sources/
```

Originals are analysed before the bundle, so when both mention an endpoint the finding keeps the
readable location. If a tree-sitter grammar can't load, a regex fallback yields the same shapes
at lower precision — jsrecon still runs.

```
src/jsrecon/
  fetch.py        page → <script>/modulepreload bundles, or local files
  sourcemaps.py   sourceMappingURL → sourcesContent → a path-safe tree
  parse.py        tree-sitter JS/TS → strings and calls (regex fallback)
  extract/        endpoints · graphql · routes · secrets, dedupe
  report.py       json · markdown · openapi 3.1
  cli.py          jsrecon map
```

## Recon suite

jsrecon is the sibling of **[httpcrabber](https://github.com/web3daemon/httpcrabber-client)**:
httpcrabber records what an app *does* on the wire, jsrecon reads what its code *can* do.
Run both on the same app and you get the traffic you saw and the endpoints you haven't triggered yet.

## Intended use

jsrecon reads the JavaScript a site already serves to every visitor — the same bytes your
browser downloads — and makes sense of it. Point it at an app whose API you need to understand:

- a third-party service with no public SDK or docs, so you can build a client;
- a public API you want an OpenAPI spec or a typed client for;
- a bug-bounty target within its stated scope, or a pentest you are authorised for;
- your own front-ends — including catching a secret that slipped into a build before someone else does.

It only reads what a normal page load fetches. It never breaks authentication, bypasses bot
protection or hides what it is (its User-Agent says `jsrecon`). The secret scan is defensive and
masks every value. Don't point it at systems you aren't authorised to test — you are responsible
for how you use it. See [SECURITY.md](https://github.com/web3daemon/jsrecon/blob/main/SECURITY.md).

## Roadmap

- [x] method from `fetch` options and `XMLHttpRequest.open`
- [x] client-side routes
- [x] path & query parameters, `file:line` for every finding
- [ ] typed async `httpx` + pydantic client generated from the recovered API
- [ ] an MCP server, so an agent can ask *"what endpoints does this app expose?"*
- [ ] `jsrecon watch` — re-run on a schedule and alert on API drift
- [ ] read [httpcrabber](https://github.com/web3daemon/httpcrabber-client) sessions as input

Building it in public: [t.me/web3daemon_social](https://t.me/web3daemon_social) ·
[X @web3daemon](https://x.com/web3daemon).

## Contributing

Issues and pull requests are welcome.

```bash
pip install -e ".[dev]"
ruff check src tests scripts && pytest
python examples/shop/build.py     # rebuild the demo shop (needs Node.js)
python scripts/gen_demo.py        # re-record assets/demo.svg from a real run
```

## License

[MIT](https://github.com/web3daemon/jsrecon/blob/main/LICENSE)
