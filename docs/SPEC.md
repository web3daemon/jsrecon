# jsrecon — technical specification

Status: v0.2. This is the working spec; sections marked _(planned)_ are not built yet.

## 1. Goal

A single `pip install` Python tool that turns a web app's client-side JavaScript
into a structured map of its API. It should beat the popular regex scanners on
precision (it parses the AST) and go further than any of them by unpacking source
maps and exporting an OpenAPI skeleton and, later, a typed client and an MCP
server.

The wider aim is a small **recon suite** that shares one session format with
[httpcrabber](https://github.com/web3daemon/httpcrabber-client): httpcrabber
records the traffic, jsrecon reads the code.

## 2. Non-goals / policy

- Not an exploitation or evasion tool. No auth bypass, no anti-bot defeat, no
  stealth. It reads only what a normal page load already fetches.
- The secret scan is **defensive**: it flags server credentials that should not
  be in a client bundle so the owner can remove them, and masks every value.
- Intended for your own apps, public APIs, and authorized security work. This is
  stated in the README and printed nowhere misleading.

## 3. Users & use cases

- Backend/integration devs building a client for an app that has no public SDK.
- Bug-bounty hunters mapping a target's attack surface (within scope).
- Front-end teams auditing what their build leaks.
- AI agents that need an API description of a site _(via the planned MCP server)_.

## 4. Architecture

```
fetch ─► [assets]
             │  (for each asset)
             ├─► sourcemaps.load ─► write originals ─► analyze_code
             └─► analyze_code
                     │  parse (tree-sitter, regex fallback)
                     ├─► extract.endpoints
                     ├─► extract.graphql
                     └─► extract.secrets
                             ▼
                        Analysis.dedupe ─► report (table / json / md / openapi)
```

Modules (`src/jsrecon/`):

| module | responsibility |
|---|---|
| `fetch.py` | collect JS from a URL (page → script srcs, or direct .js) or local path; carry a per-asset resolver for source maps |
| `sourcemaps.py` | find `sourceMappingURL`, load inline/relative maps, recover `sourcesContent`, write a path-safe tree |
| `parse.py` | tree-sitter JS/TS parse → strings & calls; regex fallback with the same shapes |
| `extract/endpoints.py` | HTTP client calls (method known) + API-shaped literals (candidates) |
| `extract/graphql.py` | `query`/`mutation`/`subscription` ops in tags and strings |
| `extract/secrets.py` | narrow, masked scan for client-leaked server credentials |
| `extract/__init__.py` | `Analysis` model, per-file and per-run aggregation, dedupe |
| `report.py` | JSON, Markdown, OpenAPI 3.1 skeleton |
| `cli.py` | `jsrecon map …`, rich console output, `--out` writer |

## 5. CLI

```
jsrecon map <url|path> [-o DIR] [--json] [--no-secrets] [--timeout N]
```
`jsrecon <target>` is shorthand for `jsrecon map <target>`. `--out` writes
`findings.json`, `findings.md`, `openapi.json`, and `sources/` (recovered tree).

## 6. Precision rules

- **Endpoints from calls** are high confidence: the string is the first argument
  of a recognised HTTP client, method taken from the callee (`.post`→POST) or
  defaulted to GET.
- **Endpoints from literals** are candidates: absolute `http(s)` URLs, or `/paths`
  that look API-shaped (`/api`, `/v1`, `/graphql`, ≥2 segments…). Asset files
  (`.js/.css/.png/…`) are excluded.
- Dedupe: a `call` for a URL outranks a bare `literal` for the same URL.
- Template strings keep their shape: each `${expr}` becomes a `{name}` placeholder
  (`/orders/${id}/refund` → `/orders/{id}/refund`); minifier names (1–2 letters,
  except `id`) become `{param}`. A template that *starts* with `${…}` has no static
  anchor and is skipped.
- A verb method (`.get/.post/…`) on an API-shaped path counts as a call even when
  the object was renamed by the minifier (`s.get("/api/orders")`). An API-shaped
  argument of an unknown callee is kept as a `literal` candidate.
- Every finding carries `source` + `line`. Recovered originals are analysed before
  their bundle, and dedupe keeps the first finding, so locations point at the
  original file. Placeholders are compared by position (`{id}` ≡ `{param}`).

## 7. Known limitations (v0.2)

- Paths built entirely by interpolation (`` `${base}${path}` ``) can't be
  resolved statically.
- No TS-in-`.js` detection beyond file extension.

## 8. Roadmap (priority order)

1. ~~method from `fetch` options and XHR `.open`~~ — done in v0.2.
2. ~~client-side routes~~ — done in v0.2; **feature flags** still open.
3. ~~OpenAPI path/query params from templates~~ — done in v0.2; still open: infer
   `/users/42` + `/users/77` → `/users/{id}` from literal samples, request bodies.
4. **typed client generator**: async `httpx` + pydantic from the recovered API,
   with auth/token flow inferred from several request samples.
5. **MCP server**: `jsrecon serve` exposing `list_endpoints` / `describe_endpoint`.
6. **`jsrecon watch`**: re-run on a schedule, diff the schema, alert on drift
   (the private-API change monitor).
7. **httpcrabber bridge**: read a recorded session (JSONL) as an input source,
   correlating observed traffic with the code that issues it.

## 9. Quality bar

- `pytest` green; every extractor has a fixture test.
- Runs with **zero config**, one command, on both a URL and a local dir.
- Works even if tree-sitter grammars fail to load (regex fallback).
- Never prints a full secret value.

## 10. Growth plan (channel / socials)

Each shipped capability = one artifact in the web3daemon style:
- README demo GIF (terminal cast of `jsrecon map` on a real, in-scope target).
- A 1-bit reel cut to the beat, same kit as the httpcrabber reel.
- A `// devlog` post per milestone to `t.me/web3daemon_social`, cross-posted to X.
- A Show HN / X launch when the typed-client or MCP milestone lands, with a GIF
  and a single sharp claim ("point it at a site, get its API").
