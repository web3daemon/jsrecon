"""jsrecon command line.

    jsrecon map <url|path> [--out DIR] [--json] [--md] [--openapi] [--no-secrets]

Fetches the JavaScript, unpacks any source maps, parses it and prints what it
found. With --out it also writes the recovered original sources and the reports.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .extract import Analysis, analyze_code
from .fetch import Loader
from . import report, sourcemaps


def _run_map(args: argparse.Namespace) -> int:
    from rich.console import Console
    from rich.table import Table

    console = Console(stderr=False)
    err = Console(stderr=True)
    out_dir = Path(args.out) if args.out else None
    src_dir = out_dir / "sources" if out_dir else None

    with Loader(timeout=args.timeout) as loader:
        try:
            assets = loader.collect(args.target)
        except RuntimeError as e:
            err.print(f"[red]error:[/red] {e}")
            return 2
        if not assets:
            err.print("[yellow]no JavaScript found at that target.[/yellow]")
            return 1

        total = Analysis()
        with console.status("[bold]analysing…", spinner="line"):
            for asset in assets:
                total.merge(analyze_code(asset.text, asset.label))
                sm = sourcemaps.load(asset.text, asset.map_base, asset.fetch)
                if sm is None:
                    continue
                for name, content in sm.originals():
                    total.merge(analyze_code(content, name))
                if src_dir is not None:
                    sourcemaps.write_originals(sm, src_dir)
    total.dedupe()

    if not args.no_secrets:
        total.secrets = total.secrets
    else:
        total.secrets = []

    _print_summary(console, total, args.target, len(assets))

    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "findings.json").write_text(report.to_json(total, args.target), encoding="utf-8")
        (out_dir / "findings.md").write_text(report.to_markdown(total, args.target), encoding="utf-8")
        (out_dir / "openapi.json").write_text(json.dumps(report.to_openapi(total, args.target), indent=2), encoding="utf-8")
        err.print(f"[green]wrote[/green] {out_dir}/ (findings.json, findings.md, openapi.json"
                  + (", sources/" if src_dir and src_dir.exists() else "") + ")")

    if args.json:
        print(report.to_json(total, args.target))
    return 0


def _print_summary(console, a: Analysis, target: str, n_assets: int) -> None:
    from rich.table import Table

    console.rule(f"[bold]jsrecon[/bold] {target}")
    console.print(f"{n_assets} asset(s) · {len(a.sources)} source file(s) parsed\n")

    if a.endpoints:
        t = Table(title=f"Endpoints ({len(a.endpoints)})", title_justify="left", header_style="bold")
        t.add_column("Method"); t.add_column("URL", overflow="fold"); t.add_column("Conf"); t.add_column("Line", justify="right")
        for e in a.endpoints[:200]:
            style = "cyan" if e.kind == "call" else "dim"
            t.add_row(e.method or "—", e.url, f"[{style}]{e.kind}[/{style}]", str(e.line))
        console.print(t)
    if a.graphql:
        t = Table(title=f"GraphQL ({len(a.graphql)})", title_justify="left", header_style="bold")
        t.add_column("Op"); t.add_column("Name"); t.add_column("Line", justify="right")
        for g in a.graphql[:100]:
            t.add_row(g.operation, g.name, str(g.line))
        console.print(t)
    if a.secrets:
        t = Table(title=f"Secrets not meant for the client ({len(a.secrets)})", title_justify="left", header_style="bold red")
        t.add_column("Sev"); t.add_column("Kind"); t.add_column("Preview"); t.add_column("Line", justify="right")
        for s in a.secrets[:100]:
            t.add_row(s.severity, s.label, s.preview, str(s.line))
        console.print(t)
    if not (a.endpoints or a.graphql or a.secrets):
        console.print("[dim]nothing recognised.[/dim]")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="jsrecon", description="Map a web app's JavaScript to its API.")
    p.add_argument("--version", action="version", version=f"jsrecon {__version__}")
    sub = p.add_subparsers(dest="command")

    m = sub.add_parser("map", help="analyse a URL or local .js files")
    m.add_argument("target", help="page URL, .js URL, file, or directory")
    m.add_argument("-o", "--out", help="write recovered sources and reports into this directory")
    m.add_argument("--json", action="store_true", help="also print findings as JSON to stdout")
    m.add_argument("--no-secrets", action="store_true", help="skip the client-secret audit")
    m.add_argument("--timeout", type=float, default=20.0, help="HTTP timeout, seconds (default 20)")
    m.set_defaults(func=_run_map)
    return p


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    # allow `jsrecon <target>` as shorthand for `jsrecon map <target>`
    if argv and argv[0] not in ("map", "-h", "--help", "--version"):
        argv.insert(0, "map")
    args = build_parser().parse_args(argv)
    if not getattr(args, "command", None):
        build_parser().print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
