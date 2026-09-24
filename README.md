<div align="center">

# jsrecon

### Map a web app's JavaScript to its API

Point it at a page. It unpacks source maps, parses every bundle with a real
JavaScript grammar, and hands you the endpoints, GraphQL operations, routes and
config the front-end talks to — as a table, JSON, Markdown, or an OpenAPI skeleton.

</div>

```bash
pipx install jsrecon        # or: pip install jsrecon inside a venv
jsrecon map https://example.com --out recon
```

```
──────────────────── jsrecon https://example.com ────────────────────
7 asset(s) · 34 source file(s) parsed

Endpoints (18)
 POST  /api/orders                 call
 GET   /api/users                  call
 GET   https://api.example.com/v2  literal
 …
GraphQL (3)
 query     GetUser
 mutation  Checkout
Secrets not meant for the client (1)
 high  AWS access key id  AKIA…LE (20 chars)  api.ts:42
```

## Why

Grepping a minified bundle for `/api/` gives you noise: strings that were never
URLs, and URLs that were split across a `+` so the regex never sees them.
jsrecon parses the bundle with [tree-sitter](https://tree-sitter.github.io/),
so it reads the code the way the engine does — a renamed `fetch`, a templated
path, an endpoint built from a base constant all still resolve.

And when a bundle ships a **source map**, the original TypeScript is sitting
right inside it. jsrecon writes that tree back to disk and reads *that* instead
of the minified soup — real names, real comments, real structure.

## What it finds

| | |
|---|---|
| 🌐 **HTTP endpoints** | `fetch` / `axios` / `ky` / `$.ajax` calls with their method, plus API-shaped path and URL literals |
| 🧬 **GraphQL** | `query` / `mutation` / `subscription` operations, in `gql\`…\`` tags and plain strings |
| 🗺 **Source maps → sources** | `sourcesContent` unpacked into the original file tree, then analysed too |
| 🔑 **Leaked server secrets** | a narrow, defensive scan for credentials that should never reach a browser (masked in output) |
| 📤 **Reports** | live table, `findings.json`, `findings.md`, and an OpenAPI 3.1 skeleton |

## Use

```bash
jsrecon map https://app.example.com          # crawl a page's scripts
jsrecon map https://app.example.com/main.js  # one bundle
jsrecon map ./dist                           # a local build directory
jsrecon map ./app.min.js --out recon --json  # write reports + print JSON
```

## Intended use

jsrecon reads the JavaScript a site already serves to every visitor — the same
bytes your browser downloads — and makes sense of it. Point it at any app whose
API you need to understand:

- a third-party service with no public SDK or docs, so you can build a client;
- a public API you want a typed client or an OpenAPI spec for;
- a bug-bounty target within its stated scope, or a pentest you have permission for;
- your own front-ends — including catching a secret that slipped into a build.

It's a reverse-engineering tool in the same spirit as
[httpcrabber](https://github.com/web3daemon/httpcrabber-client), LinkFinder or
mitmproxy2swagger: it only reads what a normal page load fetches, and it never
breaks authentication, bypasses bot protection, or hides what it is. Don't point
it at systems you aren't authorized to test — you are responsible for how you use it.

## Roadmap

- [ ] typed async `httpx` + pydantic client generation from the recovered API
- [ ] an MCP server so an agent can ask "what endpoints does this app expose?"
- [ ] client-side routes and feature flags
- [ ] `jsrecon watch` — re-run on a schedule and alert on API schema drift
- [ ] reuse [httpcrabber](https://github.com/web3daemon/httpcrabber-client) sessions as input

## License

MIT
